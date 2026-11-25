# Day 015 · Eye in Eye

A live close-up of both eyes from Pupil Labs Neon. Optical flow follows small details across the eye video. Nearby points form larger boxes with connecting lines, and each pupil carries a diameter readout when measurements are available.

A blink changes the tracking color and plays a short descending tone. Three quick blinks ignite rings of flame around the pupils. The flames roll inward, with short jets and sparks at the rim and a stereo crackle while visible. Three more quick blinks extinguish them. The maximum gap between successive blinks is 0.45 seconds.

[Open the TouchDesigner project](Day15-Eye-in-Eye.toe) · [Watch the isolated flame preview (silent)](media/fire-ring.mp4)

## Run on a Mac

1. Connect Neon Companion and the Mac to the same network. The project was built with TouchDesigner 2025.33230 and uses FFmpeg at `/opt/homebrew/bin/ffmpeg`.
2. Start the TD-Neon bridge with the Companion IP and OSC port **9000**. For the command-line bridge, see the [bridge source](../012-gaze-fluid/neon_bridge.py) and [Python requirements](../012-gaze-fluid/requirements-live.txt). From the repository root run `python days/012-gaze-fluid/neon_bridge.py --port 9000 live --device YOUR_NEON_IP` in the configured Python environment.
3. Open **Day15-Eye-in-Eye.toe**. The eye-video receiver follows the IP saved by the TD-Neon Mac app. For manual setup, set the **Neon Eye RTSP** parameter on `/project1/Day15` to `rtsp://YOUR_NEON_IP:8086/?camera=eyes`.
4. View `out_eye_flow` for the composite, also configured as the network backdrop. Audio plays through the default output device.

The project embeds the callbacks. The accompanying Python files provide editable copies of the video receiver, tracking and connections, procedural fire, and audio synthesis.
