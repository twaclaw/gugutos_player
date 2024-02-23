import asyncio
import argparse
import json
import logging
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional
from app.nfc import PN532, Status
import random
import subprocess
from systemd import journal

logger = logging.getLogger('guguto-watchdog')
logger.propagate = False
logger.addHandler(journal.JournaldLogHandler())
logger.setLevel(logging.INFO)


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

    d = sp.devices()

    restart = True
    if 'devices' in d and len(d) > 0:
        for di in d['devices']:
            if di['name'] == 'Moode Spotify':
                restart = False

    if restart:
        logger.warning("Restarting Spotify render: moodeutl -R --spotify")
        subprocess.Popen(['moodeutl', '-R', '--spotify'])


if __name__ == '__main__':
    asyncio.run(main())
