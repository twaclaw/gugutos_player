import asyncio
import argparse
import json
import logging
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.nfc import PN532

logger = logging.getLogger('guguto-main')

curr_reg = re.compile(
    r'^https\:\/\/open\.spotify\.com\/(?P<type>(?:track|album))?[/](?P<id>.*)$')
tag_reg = re.compile(r'^spotify[:](?P<type>(?:track|album))?[:](?P<id>.*)$')


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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=str, help="JSON configuration file")
    parser.add_argument("cache", type=str, help="authentication cache")

    try:
        args = parser.parse_args()
    except Exception as ex:
        logger.error("Argument parsing failed!")
        raise ex

    try:
        with open(args.config, "rb") as f:
            conf = json.load(f)
    except Exception as ex:
        logging.error("Invalid configuration file!")
        raise ex

    secrets = conf['secrets']
    device_id = conf['sound']['device_id']
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
    while True:
        pn532 = await PN532().ainit()
        tag_id_ = await pn532.read_passive_target(timeout=3)
        if tag_id_:
            tag_id = tag_id_.hex()
            tag = tags.get(tag_id, None)
            if tag and tag_id != prev_tag:
                # current = sp.currently_playing()
                # if current:
                #     current_track = current['item']['external_urls']['spotify']
                #     progress = current['progress_ms']
                #     duration = current['item']['duration_ms']
                #     print(f"Progress: {progress} {duration}")
                #     if compare_tracks(current_track, tag['uri']):
                #         # ignore, it is the same track already playing
                #         print("IGNORING")
                #     else:
                #         print(f"current track: {current_track}")
                logger.info(f"Playing {tag['name']} {tag['uri']}")
                print(f"Playing {tag['name']} {tag['uri']}")
                sp.start_playback(device_id=device_id, uris=[tag['uri']])
                prev_tag = tag_id
        else:
            prev_tag = None

        await asyncio.sleep(3)

if __name__ == '__main__':
    asyncio.run(main())
