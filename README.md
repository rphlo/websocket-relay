# Live MPEG Relay – MPEG1 Video & MP2 Audio Decoder in JavaScript

## Streaming via WebSockets

JSMpeg can connect to a WebSocket server that sends out binary MPEG-TS data. When streaming, JSMpeg tries to keep latency as low as possible - it immediately decodes everything it has, ignoring video and audio timestamps altogether. To keep everything in sync (and latency low), audio data should be interleaved between video frames very frequently (`-muxdelay` in ffmpeg).

A separate, buffered streaming mode, where JSMpeg pre-loads a few seconds of data and presents everything with exact timing and audio/video sync is conceivable, but currently not implemented.

The internal buffers for video and audio are fairly small (512kb and 128kb respectively) and JSMpeg will discard old (even unplayed) data to make room for newly arriving data without much fuzz. This could introduce decoding artifacts when there's a network congestion, but ensures that latency is kept at a minimum. If necessary You can increase the `videoBufferSize` and `audioBufferSize` through the options.

This implement a tiny WebSocket "relay", written in Python. This server accepts an MPEG-TS source over HTTP and serves it via WebSocket to all connecting Browsers. The incoming HTTP stream can be generated using [ffmpeg](https://ffmpeg.org/), [gstreamer](https://gstreamer.freedesktop.org/) or by other means.

The split between the source and the WebSocket relay is necessary, because ffmpeg doesn't speak the WebSocket protocol. However, this split also allows you to install the WebSocket relay on a public server and share your stream on the Internet (typically NAT in your router prevents the public Internet from connecting _into_ your local network).

In short, it works like this:

1. run the websocket-relay.py
2. run ffmpeg, send output to the relay's HTTP port
3. connect JSMpeg in the browser to the relay's Websocket port


## Example Setup for Streaming: Live Webcam

For this example, ffmpeg and the WebSocket relay run on the same system. This allows you to view the stream in your local network, but not on the public internet.

This example assumes that your webcam is compatible with Video4Linux2 and appears as `/dev/video0` in the filesystem. Most USB webcams support the UVC standard and should work just fine. The onboard Raspberry Camera can be made available as V4L2 device by loading a kernel module: `sudo modprobe bcm2835-v4l2`.


1) Install ffmpeg (See [How to install ffmpeg on Debian / Raspbian](http://superuser.com/questions/286675/how-to-install-ffmpeg-on-debian)). Using ffmpeg, we can capture the webcam video & audio and encode it into MPEG1/MP2.

2) Clone this repository (or just download it as ZIP and unpack)
```
git clone https://github.com/rphlo/websocket-relay.git
```

3) Change into the websocket-relay/ directory
`cd websocket-relay/`

4) Install the requirements  
`pip install requirements.txt`


5) Start the Websocket relay. Provide a password and a port for the incomming HTTP video stream and a Websocket port that we can connect to in the browser:  
`python websocket-relay.py --secret=supersecret --port=8888`

6) Open the streaming website in your browser.
`http://127.0.0.1:8888/`

7) In a third terminal window, start ffmpeg to capture the webcam video and send it to the Websocket relay. Provide the password and port (from step 7) in the destination URL:
```
ffmpeg \
	-f v4l2 \
		-framerate 25 -video_size 640x480 -i /dev/video0 \
	-f mpegts \
		-codec:v mpeg1video -s 640x480 -b:v 1000k -bf 0 \
	http://localhost:8888/upload/supersecret
```

You should now see a live webcam image in your browser. 

If ffmpeg failed to open the input video, it's likely that your webcam does not support the given resolution, format or framerate. To get a list of compatible modes run:

`ffmpeg -f v4l2 -list_formats all -i /dev/video0`


To add the webcam audio, just call ffmpeg with two separate inputs.

```
ffmpeg \
	-f v4l2 \
		-framerate 25 -video_size 640x480 -i /dev/video0 \
	-f alsa \
		-ar 44100 -c 2 -i hw:0 \
	-f mpegts \
		-codec:v mpeg1video -s 640x480 -b:v 1000k -bf 0 \
		-codec:a mp2 -b:a 128k \
		-muxdelay 0.001 \
	http://localhost:8888/upload/supersecret
```

Note the `muxdelay` argument. This should reduce lag, but doesn't always work when streaming video and audio - see remarks below.


## Some remarks about ffmpeg muxing and latency

Adding an audio stream to the MPEG-TS can sometimes introduce considerable latency. I especially found this to be a problem on linux using ALSA and V4L2 (using AVFoundation on macOS worked just fine). However, there is a simple workaround: just run two instances of ffmpeg in parallel. One for audio, one for video. Send both outputs to the same Websocket relay. Thanks to the simplicity of the MPEG-TS format, proper "muxing" of the two streams happens automatically in the relay.

```
ffmpeg \
	-f v4l2 \
		-framerate 25 -video_size 640x480 -i /dev/video0 \
	-f mpegts \
		-codec:v mpeg1video -s 640x480 -b:v 1000k -bf 0 \
		-muxdelay 0.001 \
	http://localhost:8888/upload/supersecret

# In a second terminal
ffmpeg \
	-f alsa \
		-ar 44100 -c 2 -i hw:0 \
	-f mpegts \
		-codec:a mp2 -b:a 128k \
		-muxdelay 0.001 \
	http://localhost:8888/upload/supersecret
```
In my tests, USB Webcams introduce about ~180ms of latency and there seems to be nothing we can do about it. The Raspberry Pi however has a [camera module](https://www.raspberrypi.org/products/camera-module-v2/) that provides lower latency video capture.

To capture webcam input on Windows or macOS using ffmpeg, see the [ffmpeg Capture/Webcam Wiki](https://trac.ffmpeg.org/wiki/Capture/Webcam).

