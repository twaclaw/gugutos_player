import argparse
import asyncio
import json
import logging
import random
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from systemd import journal

from app.nfc import PN532, Status

logger = logging.getLogger("guguto-player")
logger.propagate = False
logger.addHandler(journal.JournaldLogHandler())
logger.setLevel(logging.INFO)


def get_type(uri: str | list[str]) -> str | None:
    if isinstance(uri, list):
        return "list"

    tag_reg = re.compile(
        r"^spotify[:](?P<type>(?:track|album|playlist))?[:](?P<id>.*)$"
    )
    m = tag_reg.match(uri)
    if m:
        md = m.groupdict()
        return md["type"]
    return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help="JSON configuration file")
    parser.add_argument("secrets", type=str, help="JSON secrets configuration file")
    parser.add_argument("cache", type=str, help="authentication cache")

    try:
        args = parser.parse_args()
    except Exception as ex:
        logger.error("Argument parsing failed!")
        raise ex

    try:
        with open(args.config, "rb") as f:
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
            redirect_uri="http://localhost:8080",
            cache_path=args.cache,
        )
    )

    pn532 = PN532()

    tags = conf["tags"]
    prev_tag = None
    await pn532.ainit()
    devId = await pn532.reset_device()
    logger.info(f"Initilized PN532 {devId}")

    nStat = 10
    stats = [0] * nStat
    i = 0

    cache: dict = {}

    while True:
        status, response = await pn532.read_passive_target(timeout=1)
        stats[i] = status > Status.TIMEOUT
        i = (i + 1) % nStat
        if sum(stats) > nStat * 0.75:
            await pn532.reset_device()
            continue

        # XXX: noisy, spurious statusses comming from the RFID reader
        status &= 0x1  # ignore statusses other than 0x1

        if status == Status.OK:
            tag_id = response.hex()
            tag = tags.get(tag_id)
            if tag and tag_id != prev_tag:
                tracks = tag["tracks"]
                track_id = cache.get(tag_id, 0)

                if len(tracks) > 1:
                    track_id = (track_id + 1) % len(tracks)

                    # avoid playing the same track for figurines with multiple tracks
                    # piece = random.choice(tracks)
                    cache[tag_id] = track_id

                piece = tracks[track_id]

                t = get_type(piece["uri"])
                uris = piece["uri"] if t == "list" else [piece["uri"]]
                if piece.get("shuffle", False) and len(uris) > 1:
                    uris = random.sample(uris, len(uris))
                logger.debug(f"Playing {piece['name']}: {len(uris)} pieces")

                if t == "album" or t == "playlist":
                    sp.start_playback(device_id=device_id, context_uri=uris)
                else:
                    sp.start_playback(device_id=device_id, uris=uris)

                prev_tag = tag_id

            if tag is None:
                logger.warning(f"Unrecognized tag: {tag_id}")
        else:
            prev_tag = None

        delay = conf["sound"].get("polling_delay_secs", 1.0)
        await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
