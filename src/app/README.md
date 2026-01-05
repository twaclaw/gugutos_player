# Detailed setup instructions

## Preparation

- Create a Spotify app at [https://developer.spotify.com/](https://developer.spotify.com/), use `http://127.0.0.1:8888/callback` as Redirect URI.
- Get the client ID and client secret, and populate the `secrets.json` file following [this template](../config/secrets-template.json).
- Connecting to the Spotify API requires a one-time authentication token. Obtaining this token requires a desktop environment (maybe there is a workaround). If you have a headless RPi, you can run the script [get_cache](../src/scripts/get_cache.py) from your laptop to get the token and store it in `cache.txt`:

```bash
# Install the non-RPi dependencies only
git clone https://github.com/twaclaw/gugutos_player.git guguto
cd guguto
# You can use something different than uv if you want
uv venv --python=3.13
source .venv/bin/activate
uv pip install . # Do not install the RPi dependencies (.[rpi])
get_cache secrets.json # this will open the browser and creates .cache
cp .cache cache.txt
```

## Instructions

- Set up a Raspberry Pi with [moOde](https://moodeaudio.org/), this can be done directly using rpi-imager.
- Using the moOde web interface (open a browser and go to `http://moode.local` or the corresponding IP), under `audio`, configure the audio output to use the desired sound card. Under `renderers` configure and enable `Spotify Connect` (for instance format: S32 and bitrate: 320kbps).
- Install potentially required system packages:

```bash
sudo apt update
sudo apt install libsystemd-dev
sudo apt install python3-lgpio liblgpio-dev
```

- Clone this repository in the RPi. From now on, I am assuming the repository is in `/home/pi/guguto`, adjust accordingly if you put it somewhere else.

```bash
git clone https://github.com/twaclaw/gugutos_player.git guguto
cd guguto
```

- Create a Python virtual environment and install the dependencies

For instance using [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv venv --python=3.13
source .venv/bin/activate
uv pip install -e .[rpi]
```

- Copy the `secrets.json` and `cache.txt` files to `/home/pi/guguto`
- Create a [configuration file](../conf.json). Only the `general` section is required. The `tags` section can be filled later.
- If `general.use_rfid_control` is set to `true`, the PN532 NFC hat must be connected.
  - If the serial port is configured to the default: `/dev/ttyAMA0`
  - Edit `/boot/firmware/config.txt` to enable the UART, adding the line `dtoverlay=uart0`
  - Use `raspi-config` to enable the serial port and disable the serial console
  - Reboot
- Configure and start the systemd services

```bash
cp /home/pi/guguto/config/systemd/user/player.service /home/pi/.config/systemd/user

systemctl --user enable player.service
loginctl enable-linger

systemctl --user start player.service

systemctl --user status player.service
```

### Control mechanism 1: RFID tags

The PN532 NFC hat must be connected and correctly configured. Make sure that the jumpers are in the "serial" configuration, the serial port is correctly configured, and the `systemd` service is running.

The `systemd` status (`journalctl -e`) offers a mechanism to discover the UIDs of new tags. When a new tag is scanned, its UID is printed in the log output. Then add the corresponding entry in the `tags` section of the configuration file. Keep in mind that the UIDs in [conf.json](../conf.json) are only examples and will not work in your case.

### Control mechanism 2: Web UI

#### Installation

- Install Node.js and `npm` (TODO: add instructions)
- cd `frontend`

```bash
npm install
npm run build
```

```bash
cp /home/pi/guguto/config/systemd/user/ui.service /home/pi/.config/systemd/user

systemctl --user enable ui.service
loginctl enable-linger

systemctl --user start ui.service

systemctl --user status ui.service
```

#### Configuring autostart of the web UI

See [this tutorial](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/) for reference:

```bash
sudo apt update
sudo apt -y full-upgrade
sudo apt install wtype
echo > .config/labwc/autostart <<EOL
chromium localhost:3000 --kiosk --noerrdialogs --disable-infobars --no-first-run --enable-features=OverlayScrollbar --start-maximized

EOL
```

TBD ...

## Miscellaneous

### PN532 driver

**Note:** make sure the jumpers in the PN532 NCF hat are in the "serial" configuration.

The RFID hat code is based on the code provided by [Waveshare](https://www.waveshare.com/wiki/PN532_NFC_HAT). I couldn't get the SPI version to work, nor could I get the serial IRQ to work (there is a branch where I attempted that but the IRQ pin is not raising). So, I ended up implementing an asynchronous polling driver based on the serial interface.

### Spotify connect

moOde uses `librespot` to provide Spotify Connect functionality. Here are some commands that might be useful to debug potential issues.

Information about the available audio devices can be obtained with:

```bash
librespot --device ?
```

To verify if `librespot` is advertising the device, run from a device in the same network:

```bash
dns-sd -B _spotify-connect._tcp
```

The `moodeutl` command can be used to control the spotify process:

```bash
moodeutl -R --spotify # restart
moodeutl  -Ro --spotify on [off]
```

### Switching from a headless RPi to a desktop environment

```bash
sudo apt update
sudo apt full-upgrade
sudo apt install rpd-wayland-core
# optionally
sudo apt install rpd-theme rpd-preferences
# select desktop interface
sudo raspi-config
# - Go to **1 System Options** -> **S5 Boot / Auto Login**.
# - Select **B3 Desktop** (or **B4 Desktop Autologin**).
```
