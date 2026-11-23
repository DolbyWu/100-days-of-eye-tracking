# Day 013 · Eye Bounce

Two live images of the wearer's eyes float over a mirror view from the Mac camera. Gaze steers both circles. Stretch out a finger and an eye can bounce off it. Bring your thumb and index finger to the edge of one eye, pinch and drag. The eye stretches gently along the movement. Open your fingers and it settles for 0.2 seconds before gaze takes over again. Each hand can hold a different eye.

## Run on a Mac

1. Download the whole Day 013 folder. Open **Day13-Eye-Circles-Pinch.toe** in TouchDesigner. Keep the executable **day13-hands** beside it. On the project’s **Eye Bounce** parameter page, live mode uses **Mac Camera** and **Hand Collision** on, with **Simulated Gaze and Hand** off.
2. Allow TouchDesigner to use the Mac camera. On **mac_camera**, select the built-in device if the background is blank. Open **/project1/day13_eye_bounce/out_picture** in a viewer. Raise a hand in front of the computer camera. Mint lines should follow your wrist and fingers, even before Neon is connected.
3. Connect Neon to Companion and put the Mac and Companion on the same network. Open the Day 012 **TD-Neon** app, use live mode with eye features and send to OSC port **9012**. The bridge supplies gaze and the live eye-video address. Close another TouchDesigner project if it is already listening on that port. For an older launcher, enable **Manual Eye Video URL** and paste the *Eye RTSP* address reported by the bridge. [Day 012 bridge and Mac setup](../012-gaze-fluid/)
4. Raise an open hand, bring thumb and index finger to an eye, then close them to grab it. Keep both fingertips in view as you move. Releasing the pinch or moving the hand out of view releases the eye. **Mirror Camera and Gaze** controls the horizontal orientation of the camera, skeleton and steering.

To try the composition without hardware, enable **Simulated Gaze and Hand**. The two illustrated eyes drift and bounce against a simulated hand. Use live mode for finger pinching.

## Project files

| File | Role |
| --- | --- |
| [Day13-Eye-Circles-Pinch.toe](Day13-Eye-Circles-Pinch.toe) | Saved 1280×720 TouchDesigner project. |
| [motion.py](motion.py) | Gaze steering, Vision hand joints, collision, pinch ownership and elastic movement. |
| [eye_bounce.glsl](eye_bounce.glsl) | Composites the mirrored webcam, mint finger bones and the two front-facing circular crops. |
| [hands.swift](hands.swift) | Local Apple Vision tracker. The included arm64 executable reads a separate 640×360 feed and returns up to 21 joints per hand. |
| [build_td.py](build_td.py) | Rebuilds the network in a fresh project using `DAY13` as the source-folder path. |

The bundled helper is for Apple silicon. To rebuild it locally with the Xcode Command Line Tools, run `swiftc -O hands.swift -o day13-hands` inside this folder. If the file lost its executable flag during download, run `chmod +x day13-hands`.

**Development baseline.** Built on macOS with TouchDesigner 2023.12480. The live camera returned two tracked hands and 46 bone segments during verification. Scripted gesture tests covered two simultaneous grabs, stretch, release, tracking loss, bounce and return to gaze steering. For Day 014, copy this entire folder so the eye shader, motion code, project and local helper travel together.
