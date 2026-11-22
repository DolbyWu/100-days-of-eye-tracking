# Day 012 — Gaze Fluid

> What if looking did not simply select or control an object, but introduced forces into a world that continued to move beyond our gaze?

Gaze introduces directional momentum and cyan dye. Holding your gaze builds a vortex. A blink launches a decaying ring, and stopping gaze input leaves the fluid moving and dissipating. The simulation uses the Neon scene image as its coordinate space. A projection surface needs a separate calibration.

## 1. Run simulated gaze on macOS

Open [Day12-Gaze-Fluid.toe](Day12-Gaze-Fluid.toe) in TouchDesigner. To build from source instead, open a fresh project, go to **Dialogs → Textport and DATs**, and paste this line with the absolute path to this Day 12 folder:

```python
DAY12 = "/absolute/path/to/days/012-gaze-fluid"; exec(compile(open(DAY12 + "/build_td.py", encoding="utf-8").read(), "build_td.py", "exec"))
```

With the timeline playing at 60 FPS, run this command in the Day 12 folder:

```sh
python3 neon_bridge.py demo
```

Inside `/project1/day12_gaze_fluid`, open `VISUAL_RENDER/out_picture` and `GAZE_FEATURES/debug` in separate viewers. Look for cyan filaments, a radial pulse every three seconds, a short dwell, and then an injection gap in each eight-second cycle. The old dye should continue to move through the gap. Press Control-C to stop. The demo and replay use the Python standard library.

The Base COMP's **Fluid** page exposes **Preset**, **Port**, **Iterations**, **Force**, **Swirl**, **Drag**, **Fade**, **Radius**, and output width and height. Presets apply when selected. The fluid grid stays at 256 × 256. Save the project as a new `.toe` or export its Base COMP as a `.tox` from TouchDesigner after verifying the preview.

### Neural Signals artwork variant

Open [Day12-Neural-Signals.toe](Day12-Neural-Signals.toe) and keep the supplied image at `media/neural-background.jpg` alongside the project folder. Use the same bridge on port 9012. The render shader uses the pink artwork regions as gaze targets. Fixation builds the pink response, while the existing fluid trail lights the nearby white structure. The direct response follows gaze validity, while the fluid residue dissipates. Scene-camera UVs drive the artwork, so precise targeting on a physical display requires a surface calibration.

For the source build, run `build_td.py` and then execute `add_neural_background.py` in the same Textport using the same `DAY12` path. The artwork uses excitation and inhibition as an artistic metaphor. Gaze controls graphical responses, and the colors represent design choices. Neither is a measurement of neurotransmitter concentration or an ASD assessment.

## 2. Connect Neon

Keep one receiver on UDP 9012. Connect Neon to Companion and put the Mac and Companion on the same LAN. Enable **Compute eye state** and the available blink and fixation/saccade computations. Stop the demo before starting live mode. Use Python 3.10+ for the pinned SDK:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-live.txt
mkdir -p recordings
.venv/bin/python neon_bridge.py --record recordings/day12-01.csv live
```

On Windows use the venv's `Scripts/python.exe` and a forward-slash absolute path in the builder. The Day 12 bridge uses version 1.9.0 of the Neon SDK, matching the local verified installation. Gaze always reads binocular `x`, `y`, `worn`, and `timestamp_unix_ns` from the documented gaze variants. Per-eye pupil diameter and eyelid aperture depend on Companion and eye-state settings. The eye-events stream supplies blinks when available. Missing eye-state gives a neutral pupil brush adjustment, and spatial dwell remains available. Optional IMU is sent and logged when available. [Pupil SDK gaze](https://pupil-labs.github.io/pl-realtime-api/v1.9.0/methods/async/streaming/gaze/) · [Pupil async API](https://pupil-labs.github.io/pl-realtime-api/v1.9.0/api/async/)

Test direction and then test blink and pupil separately. For live scene video, the bridge prints the scene RTSP URL when Companion exposes it. Enter it in a Video Stream In TOP and display it alongside the fluid, or composite it downstream. The RTSP decoder introduces variable delay. Use the export replay path for frame-index synchronization. [Video Stream In TOP](https://derivative.ca/UserGuide/Video_Stream_In_TOP)

## 3. Replay and record

Export **Timeseries Data + Scene Video** from Pupil Cloud. In `RECORDING/scene_movie`, set **File** to the matching untrimmed scene MP4. Run:

```sh
python3 neon_bridge.py replay "/path/to/export-folder" --loop
```

The bridge joins `gaze.csv` and optional `3d_eye_states.csv` at integer UNIX timestamps. It reads optional blink, fixation, saccade, and IMU CSVs. For each playback instant it selects the latest `world_timestamps.csv` row at or before that instant and sends its zero-based index to `RECORDING/out_scene` via the movie TOP. The timestamps must follow the MP4's decoded frame order and increase strictly. Check the frame index in the debug viewer. Playback speed is adjustable with `--rate`. For a bridge capture paired with a timestamp-compatible scene export, pass the capture CSV as the replay source and add `--world-timestamps PATH`. [Neon recording format](https://docs.pupil-labs.com/neon/data-collection/data-format/) · [Movie File In TOP](https://derivative.ca/UserGuide/Movie_File_In_TOP)

The bridge's `--record` option writes a new raw CSV with exact integer nanoseconds and JSON payloads before OSC decimation. Record on Companion for original world video. To record the artwork, set a movie path on `RECORDING/capture` and set the COMP's **Frame sync CSV** to a new absolute path before turning on **Record**. This produces a per-render-frame sidecar containing the source session, source epoch, elapsed source and gaze time, scene index, gaze validity, and blink count. TD frame and local monotonic time identify the rendered sample. Encoders can drop frames under load, so check the Movie File Out TOP's diagnostics before treating each row as a video frame. A replay loop resets the input source generation and event counters while the fluid continues to evolve.

## TouchDesigner network

| COMP | Operators and responsibilities |
| --- | --- |
| `NEON_INPUT` | OSC In CHOP on the parent **Port**. Unqueued snapshots keep creative control current. |
| `GAZE_FEATURES` | Execute DAT, Text TOP debug panel and Script TOP parameter upload. Python uploads only a 4 × 1 RGBA32F parameter texture. Position/valid/radius, velocity/dwell/dt, wave center/age/strength and force/decay each occupy one texel. |
| `FLUID_ENGINE` | GLSL pixel passes and three persistent feedback buffers at 256 × 256 in RGBA32F. Velocity is measured in grid cells/s. The boundary wraps. |
| `VISUAL_RENDER` | GLSL integrates fine grain along projected velocity and lights it with dye density and gradient to reveal cyan and white filaments on black. View `out_picture`. |
| `RECORDING` | Frame-indexed Movie File In, `out_scene`, and Movie File Out for the artwork. The Execute DAT writes the frame sync sidecar when recording is enabled. |

The builder embeds the operators and shaders in the project. For manual inspection or reconstruction, concatenate `shaders/common.glsl` and the pass's GLSL file into its Pixel Shader DAT. Use GLSL TOP in vertex/pixel mode with a default vertex shader. Wire the inputs in this order:

| Pass | Input 0 | Input 1 | Input 2 |
| --- | --- | --- | --- |
| `velocity` | velocity feedback | parameter texture | |
| `divergence` | velocity | | |
| `pressure` | pressure feedback | divergence | |
| `project` | velocity | pressure | |
| `dye` | dye feedback | project | parameter texture |
| `render` | dye | projected velocity | |

Each Feedback TOP takes the same 256 × 256 black RGBA32F Constant TOP as its reset input. Set their targets to `project`, `pressure`, and `dye`, respectively. Set **Passes** on `pressure` to 24 initially. This repeats Jacobi with prior-pass pressure on input 0 while divergence remains on input 1. The other stages use one pass. `velocity` backtraces the previous velocity and adds forces, `project` subtracts the discrete pressure gradient, and `dye` backtraces dye with the projected velocity. The Execute DAT advances the graph once per rendered TD frame. To clear the world, pulse all three Feedback TOPs' **Reset Pulse**. [GLSL TOP](https://derivative.ca/UserGuide/GLSL_TOP) · [GLSL TOP shader conventions](https://derivative.ca/UserGuide/Write_a_GLSL_TOP) · [Feedback TOP](https://derivative.ca/UserGuide/Feedback_TOP)

## Troubleshooting and verification

- **Unable to bind** — close the duplicate receiver or select a free **Port** and use `python3 neon_bridge.py --port PORT demo`. The earlier TD-Neon launcher still runs the earlier bridge.
- **Waiting or invalid** — check the debug viewer. If the live bridge cannot discover Companion, allow Local Network access for the launching app and try `live --device IP`. The bridge retries a lost gaze connection automatically. Check worn status and scene bounds.
- **Pupil = −1** — confirm that Compute eye state is enabled and that the source exposes pupil fields. Check the active gaze track before troubleshooting optional data.
- **Shader error** — point an Info DAT at the affected GLSL TOP and inspect its compile log. Verify input order and 32-bit float intermediates. Disable a global TOP resolution multiplier for the solver.
- **Below 60 FPS** — lower render output resolution first, then reduce **Iterations** while checking the stability and look of the flow. 60 FPS is a target that requires a measurement on the installation machine.

Verification on the development Mac used Apple M4 Pro, macOS, the installed TouchDesigner 2023.12480, and Python SDK 1.9.0. The six shader passes compiled and ran at 256 × 256 in a local OpenGL test harness using compatible GLSL 4.10 and stand-ins for TouchDesigner's injected declarations. The test checked that pressure projection reduced divergence and that dye persisted and dissipated after gaze was disabled. The Python tests check the control bundle and replay logic. TouchDesigner 2023.12480 compiled and rendered the corrected GPU network with simulated OSC input. A subsequent live test received valid Neon gaze, pupil readings and blink counts, compiled the filament shader in TouchDesigner, and exported an artwork frame from the live output. Sustained 60 FPS, synchronized MP4 display, and the isolated blink response remain to be checked. [Derivative system requirements](https://derivative.ca/UserGuide/System_Requirements)

```sh
python3 -B -m unittest discover -s tests -v
clang -Wno-deprecated-declarations -framework OpenGL tests/mac_gpu_smoke.c -o /tmp/day12-gpu-smoke
/tmp/day12-gpu-smoke shaders/common.glsl shaders/velocity.glsl shaders/divergence.glsl shaders/pressure.glsl shaders/project.glsl shaders/dye.glsl shaders/render.glsl
```

[OSC schema](OSC.md) · [DIS / Research through Design reflection](REFLECTION.md)
