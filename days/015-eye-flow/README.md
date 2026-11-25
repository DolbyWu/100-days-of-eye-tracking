# Day 015 · Interactive Eye Circles

Two circular live eye feeds from Pupil Labs Neon float over the mirrored Mac camera. Pinch an eye with one hand to move it. Pinch the same eye with both hands and change the distance between them to resize it. Release to keep its position and size.

Three quick blinks cycle through fire, blue particle ripples, and a transparent clock with red calligraphy. Its hand leaves a white trail that turns electric blue near 甲、乙、丙. Keep both eyes closed for one second to return to the untreated eye video. The maximum gap between successive blinks in a triple is 0.45 seconds.

A dashboard along the bottom displays both pupil diameters, eyelid aperture, blinks, gaze and event counts, head motion and connection status.

[Open the TouchDesigner project](Day15-Interactive-Eye-Circles.toe) · [Preview the fire effect](media/fire-ring.mp4)

## Run on a Mac

1. Connect Neon Companion and the Mac to the same network. The project was built with TouchDesigner 2025.33230 and uses FFmpeg at `/opt/homebrew/bin/ffmpeg`.
2. Start the TD-Neon bridge with the Companion IP and OSC port **9000**. For the command-line bridge, see the [bridge source](../012-gaze-fluid/neon_bridge.py) and [Python requirements](../012-gaze-fluid/requirements-live.txt). From the repository root run `python days/012-gaze-fluid/neon_bridge.py --port 9000 live --device YOUR_NEON_IP` in the configured Python environment.
3. Open **Day15-Interactive-Eye-Circles.toe**. The eye-video receiver follows the IP saved by the TD-Neon Mac app. For manual setup, set the **Neon Eye RTSP** parameter on `/project1/Day15` to `rtsp://YOUR_NEON_IP:8086/?camera=eyes`.
4. View `out_camera_eyes` for the composite, also configured as the network backdrop. Audio plays through the default output device.

Keep the repository folder structure when opening the project. Hand tracking uses the macOS Vision helper in [Day 014](../014-reading-orbits/day13-hands). The clock loads `clock-stems.png` beside the project. Allow TouchDesigner to use the Mac camera.
