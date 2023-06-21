# Python code

## PN532 driver

The Python code provided by [Waveshare](https://www.waveshare.com/wiki/PN532_NFC_HAT)
is a bit buggy. I didn't manage to get the SPI version working and I didn't want to spend too much time on it; essentially, I wanted a working version without having to read any datasheet or spec. I ended up using their UART version but completly rewrote the low level part.

I would like to have an interrupt driven setup but that's something I would look at in the future. Right now, I am polling, and some details of the implementation are rather brute-force.


## Spotipy

Create an app in spotify development.

Besides the credentials provided in the configuration file, Spotify requires additional tokens to authorize a device. The first time you access a device in `spotipy`, you get URL that

* Run a modified version of the application on the PC
* `spotipy` will ask to follow a link. Open the link on a browser.

* Once the authentication is done, a `.cache` file is created.
* Copy the file to the raspberry pi to `cache.txt`



# System configuration

Run `rasp-config` to configure the sound card and enable the serial port





sudo systemctl mask serial-getty@ttyS0.service


/etc/udev/rules.d/99-com.rules
ACTION=="add", KERNEL="tty", MODE="0660"
ACTION=="add", KERNEL="ttyS0", MODE="0660"

## Initial authentication from the Raspberry Pi


Default USB sound card
cat /etc/asound.conf
defaults.pcm.card 3
defaults.ctl.card 3
defaults.pcm.dmix.rate 32000
defaults.pcm.dmix.format S16_LE
