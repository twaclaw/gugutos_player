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
    def __init__(self, source, track_info):
        self.source = source
        self.track_info = track_info


async def player_worker(queue: asyncio.Queue, sp, device_id, current_track_info: dict):
    logger.info("Player worker started")
    while True:
        req: PlayRequest = await queue.get()
        piece = req.track_info
        logger.info(f"Processing request from {req.source}: {piece.get('name')}")

        current_track_info.clear()
        current_track_info.update(piece)

        try:
            t = get_type(piece["uri"])
            uris = [piece["uri"]] if t == "track" else piece["uri"]
            if piece.get("shuffle", False) and len(uris) > 1:
                uris = random.sample(uris, len(uris))
            logger.debug(f"Playing {piece['name']}: {len(uris)} pieces")

            if t in ["playlist", "album", "show"]:
                offset = piece.get("offset", 0)
                sp.start_playback(
                    device_id=device_id, context_uri=uris, offset={"position": offset}
                )
            else:
                sp.start_playback(device_id=device_id, uris=uris)

            await asyncio.sleep(1)
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

        except Exception as e:
            logger.error(f"Error playing track: {e}")

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
                piece = track_manager.select_next_piece(tag_id, tag)
                if piece:
                    await queue.put(PlayRequest("nfc", piece))
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
            redirect_uri="http://127.0.0.1:8888/callback", # must be the same one configured in the spotify app.
            cache_path=args.cache,
        )
    )

    tags = conf["tags"]

    queue = asyncio.Queue()

    current_track_info = {}

    track_manager = TrackManager()

    tasks = [
        asyncio.create_task(player_worker(queue, sp, device_id, current_track_info)),
    ]

    if conf.get("general", {}).get("use_rfid_control", True):
        from app.nfc import PN532

        pn532 = PN532()
        tasks.append(
            asyncio.create_task(nfc_worker(queue, pn532, tags, conf, track_manager))
        )

    if conf.get("general", {}).get("use_touchscreen_control", False):
        tasks.append(
            asyncio.create_task(
                run_server(queue, conf, PlayRequest, current_track_info, track_manager)
            )
        )

    await asyncio.gather(*tasks)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
