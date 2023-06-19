sudo systemctl mask serial-getty@ttyS0.service


/etc/udev/rules.d/99-com.rules
ACTION=="add", KERNEL="tty", MODE="0660"
ACTION=="add", KERNEL="ttyS0", MODE="0660"

## Initial authentication from the Raspberry Pi

* Run a modified version of the application on the PC
* `spotipy` will ask to follow a link. Open the link on a browser.
* Once the authentication is done, a `.cache` file is created.
* Copy the file to the raspberry pi to `cache.txt`


Default USB sound card
diego@raspberrypi:~ $ cat /etc/asound.conf
defaults.pcm.card 3
defaults.ctl.card 3
defaults.pcm.dmix.rate 32000
defaults.pcm.dmix.format S16_LE
