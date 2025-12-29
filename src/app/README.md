# Python code

## PN532 driver

**Make sure the jumpers in the PN532 NCF hat are in the "serial" configuration.**

The Python code provided by [Waveshare](https://www.waveshare.com/wiki/PN532_NFC_HAT)
is a bit buggy. I couldn't get the SPI version to work and I didn't want to spend too much time on it; basically, I wanted a working version without having to read a datasheet or spec. I ended up using their UART version but rewrote the low level part.

I'd like to have an interrupt-driven setup, but that's something I'll look into in the future. Right now, I am polling, and some details of the implementation are rather brute force.

In `/boot/firmware/config.txt`, make sure to enable the UART with the following line:

```bash
dtoverlay=uart0
```

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
python src/scripts/get_cache.py secrets_file.json

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
systemctl --user enable watchdog.service
loginctl enable-linger

# start the service
systemctl --user start player.service

# check the status with
systemctl --user status player.service
```

The status can also be checked with `journalctl`. For instance, new RFID tags can be identified by scanning the tag and looking at the log output with `journalctl -e`.

# System configuration

Run `rasp-config` to configure the sound card and enable the serial port. The same serial port used by the NFC hat is also used for the console.

<details>
<summary>
Additional configuration (possibly not required)
</summary>

```bash
sudo systemctl mask serial-getty@ttyS0.service
```

To change the permissions of the port, add the following to a `.rules` file, for instance

```bash
# /etc/udev/rules.d/99-com.rules
ACTION=="add", KERNEL="tty", MODE="0660"
ACTION=="add", KERNEL="ttyS0", MODE="0660"
```

</details>

Regarding the software providing the spotify connect functionality, there are several options. I have been switching between [Moode](https://moodeaudio.org) and [Raspotify](https://github.com/dtcooper/raspotify). Moode is a very nice, self-contained audiophile project with a lot of features and a nice web user interface. If you want more control over the version of the operating system and packages, then Raspotify is a better option.

<details>
<summary>
Moode configuration
</summary>

Moode is a self-contained image including the operating system.

[Download](https://moodeaudio.org/) the image and create an SD card.

Configure Spotify to S32 320kbps in the Moode audio settings.

<details>
<summary>
Raspotify configuration
</summary>

Follow the instructions from the [basic setup](https://github.com/dtcooper/raspotify/wiki/Basic-Setup-Guide)

Verify the installation with

```bash
systemctl status raspotify
```

The configuration lives in `/etc/raspotify/conf`.

To list devices and their supported formats, run:

```bash
librespot --device ?
```

Update the relevant lines in the documentation according to the output of the previous command.

```plain
LIBRESPOT_BITRATE="320"
LIBRESPOT_FORMAT="S32"
LIBRESPOT_DEVICE="hw:CARD=PMA1700NE,DEV=0"
#TMPDIR=/tmp
```

</details>
