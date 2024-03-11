# Le carnaval des animaux

<img src="./img/animmals.jpg"></img>
## Motivation
To give my kid a way of playing his favorite music.

![](./img/video.mov)
<!-- <video src="./img/video.mov"></video> -->

I already had a Raspberry Pi running an audiophile image connected to my amplifier (which has a built-in USB sound card). [Moode](https://moodeaudio.org) (and other projects such as [Raspotify](https://github.com/dtcooper/raspotify)) implements a device for [Spotify Connect](https://support.spotify.com/us/article/spotify-connect/). **Spotify premium is required in this setup.**


## Implementation

* Attach an [NFC reader hat](https://www.waveshare.com/wiki/PN532_NFC_HAT) to the Raspberry Pi
* Build a set of figurines, each with an RFID tag
* Associate tracks (multiple tracks can be associated), or playlists, or albums to each figurine
* Run a process that plays the track (or one of the tracks) associated to the figurine 🐘🦘🐢 whenever it is placed over the reader (the track is played on the Spotify connect device specified in the configuration.)

The whole thing runs as a `systemd` process that constantly polls the NFC reader and streams the track if a valid, configured RFID is detected.

See additional details [here](./src/app/).

