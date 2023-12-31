import argparse
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

parser = argparse.ArgumentParser()
parser.add_argument("secrets", type=str, help="JSON secrets file")

try:
    args = parser.parse_args()
except Exception as ex:
    print("Argument parsing failed!")
    raise ex

try:
    with open(args.secrets, "rb") as f:
        secrets = json.load(f)

except Exception as ex:
    raise ex

secrets = secrets['secrets']
device_id = secrets['device_id']

scope = "user-read-playback-state,user-modify-playback-state"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=secrets['client_id'],
                                               client_secret=secrets['client_secret'],
                                               scope=scope,
                                               redirect_uri="http://localhost:8080"
                                               ))
print(sp.devices())
