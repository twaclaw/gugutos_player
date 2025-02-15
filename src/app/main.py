import argparse
import asyncio
import json
import logging
import random
import re
import subprocess
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from systemd import journal

from app.nfc import PN532, Status

logger = logging.getLogger('guguto-main')
logger.propagate = False
logger.addHandler(journal.JournaldLogHandler())
logger.setLevel(logging.INFO)

curr_reg = re.compile(
    r'^https\:\/\/open\.spotify\.com\/(?P<type>(?:track|album))?[/](?P<id>.*)$')
tag_reg = re.compile(r'^spotify[:](?P<type>(?:track|album|playlist))?[:](?P<id>.*)$')

_ID = '32010607e800'


def get_type(uri: str) -> Optional[str]:
    m = tag_reg.match(uri)
    if m:
        md = m.groupdict()
        return md['type']
    return None


def compare_tracks(current: str, tag: str) -> bool:
    curr_match = curr_reg.match(current)
    tag_match = tag_reg.match(tag)
    if curr_match and tag_match:
        c_dict = curr_match.groupdict()
        t_dict = tag_match.groupdict()
        c_type = c_dict.get('type', 'c')
        t_type = t_dict.get('type', 't')
        c_id = c_dict.get('id', 'c')
        t_id = t_dict.get('id', 't')

        return (c_type == t_type) and (c_id == t_id)

    return False


# global object
pn532 = PN532()


async def reset_device(ntries: int = 4, delay: float = 1) -> str:
    logger.debug("Resetting PN532")
    for _ in range(ntries):
        await pn532._reset()
        await pn532.wakeup()
        status, response = await pn532.get_firmware_version()
        if status == Status.OK:
            resp = response.hex()
            if (resp == _ID):
                return resp
        else:
            await asyncio.sleep(delay)

    raise RuntimeError("Unable to initialize PN532 device!")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help="JSON configuration file")
    parser.add_argument("secrets", type=str,
                        help="JSON secrets configuration file")
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

    secrets = secrets['secrets']
    device_id = secrets['device_id']
    scope = "user-read-playback-state,user-modify-playback-state"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=secrets['client_id'],
                                                   client_secret=secrets['client_secret'],
                                                   scope=scope,
                                                   open_browser=False,
                                                   redirect_uri="http://localhost:8080",
                                                   cache_path=args.cache
                                                   ))

    tags = conf['tags']
    prev_tag = None
    await pn532.ainit()
    devId = await reset_device()
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
            await reset_device()
            continue

        if status == Status.OK:
            tag_id = response.hex()
            tag = tags.get(tag_id, None)
            if tag and tag_id != prev_tag:
                if conf['sound']['restart_spotify']:
                    subprocess.Popen(['moodeutl', '-R', '--spotify'])

                tracks = tag['tracks']
                track_id = cache.get(tag_id, 0)

                if len(tracks) > 1:
                    track_id = (track_id + 1) % len(tracks)

                    # avoid playing the same track for figurines with multiple tracks
                    #piece = random.choice(tracks)
                    cache[tag_id] = track_id

                piece = tracks[track_id]

                volume = piece['volume'] if 'volume' in piece else conf['sound']['volume']
                logger.debug(f"Playing {piece['name']} {piece['uri']}")
                t = get_type(piece['uri'])
                sp.volume(volume, device_id=device_id)
                if t == "track":
                    sp.start_playback(device_id=device_id, uris=[piece['uri']])

                if t == "album" or t == "playlist":
                    sp.start_playback(device_id=device_id,
                                      context_uri=piece['uri'])

                prev_tag = tag_id

            if tag is None:
                logger.warning(f"Unrecognized tag: {tag_id}")
        else:
            prev_tag = None

        delay = conf['sound']['polling_delay_secs']
        await asyncio.sleep(delay)

if __name__ == '__main__':
    asyncio.run(main())
