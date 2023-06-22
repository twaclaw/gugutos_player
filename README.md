# Le carnaval des animaux

<img src="./img/animmals.jpg"></img>
## Motivation
I wanted my kid to have a way of playing his favorite music.

I already had a Raspberry Pi running [Raspotify](https://github.com/dtcooper/raspotify) connected to my amplifier (which has a built-in USB sound card). Raspotify implements a device for [Spotify Connect](https://support.spotify.com/us/article/spotify-connect/).

## Implementation

* Attach an [NFC reader hat](https://www.waveshare.com/wiki/PN532_NFC_HAT) to the Raspberry Pi
* Build a set of figurines, each with an RFID tag
* Associate tracks (or albums) to each figurine
* Run a process that plays the track associated to the figurine 🐘🦘🐢 whenever it is placed over the reader.

The whole thing runs as a `systemd` process that constantly polls the NFC reader and streams the track if a valid, configured RFID is detected.

See additional details [here](./src/app/).
