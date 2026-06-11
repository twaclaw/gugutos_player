import argparse
import asyncio
import json
import logging
import random
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

try:
    from systemd import journal
except ImportError:
    journal = None

from app.server import run_server
from app.track_manager import TrackManager

logger = logging.getLogger("guguto-player")
logger.propagate = False

if journal:
    logger.addHandler(journal.JournaldLogHandler())
else:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.setLevel(logging.INFO)


def get_type(uri: str | list[str]) -> str | None:
    if isinstance(uri, list):
        return "list"

    tag_reg = re.compile(
        r"^spotify[:](?P<type>(?:track|album|playlist|show))?[:](?P<id>.*)$"
    )
    m = tag_reg.match(uri)
    if m:
        md = m.groupdict()
        return md["type"]
    return None


class PlayRequest:
    def __init__(self, source, plan: dict):
        self.source = source
        self.autoplay = plan.get("autoplay", False)
        self.shuffle = plan.get("shuffle", False)
        self.pieces = plan.get("pieces")
        self.track_info = plan.get("track_info")


def _enrich_current_track_info(sp, current_track_info: dict):
    """Overlay the live Spotify "now playing" metadata onto current_track_info."""
    track = sp.current_user_playing_track()
    if track and track.get("item"):
        item = track["item"]
        current_track_info["name"] = item.get("name")
        artists = item.get("artists", [])
        current_track_info["artist"] = ", ".join([a["name"] for a in artists])

        album = item.get("album", {})
        images = album.get("images", [])
        if images:
            current_track_info["image"] = images[0].get("url")


def _start_piece(sp, device_id, piece: dict):
    """Start a single piece. Returns when playback has been requested."""
    t = get_type(piece["uri"])
    if t in ["playlist", "album", "show"]:
        offset = piece.get("offset", 0)
        sp.start_playback(
            device_id=device_id,
            context_uri=piece["uri"],
            offset={"position": offset},
        )
    else:
        sp.start_playback(device_id=device_id, uris=[piece["uri"]])


async def _wait_until_stopped(sp, poll_delay: float, startup_timeout: float = 10.0):
    """Block until the current playback finishes naturally.

    Used to chain pieces in autoplay mode. The task is cancelled by the player
    worker when a new request arrives, which interrupts the sleep below.
    """
    waited = 0.0
    started = False
    while waited < startup_timeout:
        playback = sp.current_playback()
        if playback and playback.get("is_playing"):
            started = True
            break
        await asyncio.sleep(poll_delay)
        waited += poll_delay

    if not started:
        return

    while True:
        playback = sp.current_playback()
        if not playback or not playback.get("is_playing"):
            return
        await asyncio.sleep(poll_delay)


async def _play_sequence(
    pieces: list[dict],
    shuffle: bool,
    sp,
    device_id,
    current_track_info: dict,
    poll_delay: float,
):
    """Play every piece in the list, one after another (autoplay).

    Consecutive track pieces are handed to Spotify in a single call so it
    auto-advances gaplessly; album/show/playlist pieces are played as a
    context. After each segment we wait for it to finish before starting the
    next one (unless it is the last segment).
    """
    pieces = list(pieces)
    if shuffle and len(pieces) > 1:
        pieces = random.sample(pieces, len(pieces))

    i = 0
    while i < len(pieces):
        if get_type(pieces[i]["uri"]) == "track":
            run = []
            while i < len(pieces) and get_type(pieces[i]["uri"]) == "track":
                run.append(pieces[i]["uri"])
                i += 1
            sp.start_playback(device_id=device_id, uris=run)
        else:
            _start_piece(sp, device_id, pieces[i])
            i += 1

        await asyncio.sleep(1)
        _enrich_current_track_info(sp, current_track_info)

        if i < len(pieces):
            await _wait_until_stopped(sp, poll_delay)


async def _handle_request(
    req: "PlayRequest", sp, device_id, current_track_info, poll_delay
):
    try:
        if req.autoplay and req.pieces:
            logger.info(f"Autoplay {len(req.pieces)} pieces from {req.source}")
            current_track_info.clear()
            current_track_info.update(req.pieces[0])
            await _play_sequence(
                req.pieces, req.shuffle, sp, device_id, current_track_info, poll_delay
            )
        else:
            piece = req.track_info
            if not piece:
                return
            logger.info(f"Processing request from {req.source}: {piece.get('name')}")
            current_track_info.clear()
            current_track_info.update(piece)
            _start_piece(sp, device_id, piece)
            await asyncio.sleep(1)
            _enrich_current_track_info(sp, current_track_info)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Error playing track: {e}")


async def player_worker(
    queue: asyncio.Queue, sp, device_id, current_track_info: dict, poll_delay: float
):
    logger.info("Player worker started")
    current = None
    while True:
        req: PlayRequest = await queue.get()

        # A new request supersedes anything in flight (e.g. an autoplay
        # sequence still chaining pieces): cancel it and take over.
        if current and not current.done():
            current.cancel()
            try:
                await current
            except asyncio.CancelledError:
                pass

        current = asyncio.create_task(
            _handle_request(req, sp, device_id, current_track_info, poll_delay)
        )
        queue.task_done()


async def nfc_worker(
    queue: asyncio.Queue, pn532, tags, conf, track_manager: TrackManager
):
    from app.nfc import Status

    logger.info("NFC worker started")
    prev_tag = None

    await pn532.ainit()
    devId = await pn532.reset_device()
    logger.info(f"Initilized PN532 {devId}")

    nStat = 10
    stats = [0] * nStat
    i = 0

    while True:
        status, response = await pn532.read_passive_target(timeout=1)
        stats[i] = status > Status.TIMEOUT
        i = (i + 1) % nStat
        if sum(stats) > nStat * 0.75:
            await pn532.reset_device()
            continue

        if status == Status.OK:
            tag_id = response.hex()
            tag = tags.get(tag_id)
            if tag and tag_id != prev_tag:
                plan = track_manager.prepare(tag_id, tag, conf.get("general", {}))
                if plan:
                    await queue.put(PlayRequest("nfc", plan))
                prev_tag = tag_id

            if tag is None:
                logger.warning(f"Unrecognized tag: {tag_id}")
        else:
            prev_tag = None

        delay = conf["sound"].get("polling_delay_secs", 1.0)
        await asyncio.sleep(delay)


async def async_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--conf", type=str, required=True, help="JSON configuration file"
    )
    parser.add_argument(
        "--secrets", type=str, required=True, help="JSON secrets configuration file"
    )
    parser.add_argument("--cache", type=str, required=True, help="authentication cache")

    try:
        args = parser.parse_args()
    except Exception as ex:
        logger.error("Argument parsing failed!")
        raise ex

    try:
        with open(args.conf, "rb") as f:
            conf = json.load(f)

        with open(args.secrets, "rb") as f:
            secrets = json.load(f)
    except Exception as ex:
        logging.error("Invalid configuration file!")
        raise ex

    secrets = secrets["secrets"]
    device_id = secrets["device_id"]
    scope = "user-read-playback-state,user-modify-playback-state"
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=secrets["client_id"],
            client_secret=secrets["client_secret"],
            scope=scope,
            open_browser=False,
            redirect_uri="http://127.0.0.1:8888/callback",  # must be the same one configured in the spotify app.
            cache_path=args.cache,
        )
    )

    tags = conf["tags"]

    queue = asyncio.Queue()

    current_track_info = {}

    track_manager = TrackManager()

    poll_delay = conf.get("sound", {}).get("polling_delay_secs", 1.0)

    tasks = [
        asyncio.create_task(
            player_worker(queue, sp, device_id, current_track_info, poll_delay)
        ),
    ]

    if conf.get("general", {}).get("use_rfid_control", True):
        from app.nfc import PN532

        port = conf.get("general").get("nfc_serial_port", "/dev/ttyAMA0")

        pn532 = PN532(port=port)
        tasks.append(
            asyncio.create_task(nfc_worker(queue, pn532, tags, conf, track_manager))
        )

    if conf.get("general", {}).get("use_touchscreen_control", False):
        tasks.append(
            asyncio.create_task(run_server(queue, conf, PlayRequest, sp, track_manager))
        )

    await asyncio.gather(*tasks)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
