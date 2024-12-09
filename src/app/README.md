# Python code

## PN532 driver

**Make sure the jumpers in the PN532 NCF hat are in the "serial" configuration.**

The Python code provided by [Waveshare](https://www.waveshare.com/wiki/PN532_NFC_HAT)
is a bit buggy. I didn't manage to get the SPI version working and I didn't want to spend too much time on it; basically, I wanted a working version without having to read any datasheet or spec. I ended up using their UART version but rewrote the low level part.

I would like to have an interrupt driven setup but that's something I would look at in the future. Right now, I am polling, and some details of the implementation are rather brute-force.

## Spotipy

[Spotipy](https://spotipy.readthedocs.io/en/latest/) is a Python library for the Spotify web API. To use this API, it is necessary to create an app at [https://developer.spotify.com/](https://developer.spotify.com/).

Besides the credentials provided in the configuration file, Spotify requires additional tokens to authorize a device. The first time you access a device in `spotipy`, you get a URL to authorize the client device for the given scope. The problem is that doing that on headless systems is not straightfoward. What I did was:

- Run the `spotipy` part of the application on my PC: `spotipy` will ask to follow a link. Open the link on a browser.
- Once the authentication is done, a `.cache` file is created.
- Copy the file to the raspberry pi to `cache.txt` (which is passed as an option to the script.)

On your PC (not on the RPi) go through the following steps in the project directory:

```bash
# Create a virtual environment, for instance
virtualenv -p python3.11 venv

# activate the venv
. venv/bin/activate

# install Spotipy (other dependendencies are not required)
pip install spotipy

# run the following script
python src/scripts/get_cache.py conf.json

# the latter should create a .cache file
```

## Installation

Clone this repo and install the Python dependencies.

```bash
git clone git@github.com:twaclaw/gugutos_player.git guguto

cd guguto`

# create a virtual env
virtualenv venv
. venv/bin/activate

# install the dependencies

# in case the systemd Python package cannot be installed
sudo apt install libsystemd-dev

pip install -e src/
```

Copy the configuration file and edit it (add the credentials, and edit the list of tags and their associated tags.)

```bash
cp config/conf-template.json conf.json
```

Make sure this location, `/home/pi/guguto`, contains also the `cache.txt` file mentioned in the previous section.

### Systemd service

```bash
cp /home/pi/guguto/config/systemd/user/player.service /home/pi/.config/systemd/user

# enable the service
systemctl --user enable player.service

# start the service
systemctl --user start player.service

# check the status with
systemctl --user status player.service
```

The status can also be checked with `journalctl`. For instance, new RFID tags can be identified by scanning the tag and looking at the log output with `journalctl -e`.

# System configuration

Run `rasp-config` to configure the sound card and enable the serial port. The same serial port used by the NFC hat is also used for the console.

```bash
sudo systemctl mask serial-getty@ttyS0.service
```

To change the permissions of the port, add the following to a `.rules` file, for instance

```bash
# /etc/udev/rules.d/99-com.rules
ACTION=="add", KERNEL="tty", MODE="0660"
ACTION=="add", KERNEL="ttyS0", MODE="0660"
```

# Moode

[Download](https://moodeaudio.org/) the image and create an SD card.

# Raspotify configuration

Follow the instructions from the [basic setup](https://github.com/dtcooper/raspotify/wiki/Basic-Setup-Guide)

<!-- #/etc/asound.conf
defaults.pcm.card 3
defaults.ctl.card 3
defaults.pcm.dmix.rate 32000
defaults.pcm.dmix.format S16_LE -->
