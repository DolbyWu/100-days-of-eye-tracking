import csv
import json
import math
from pathlib import Path
import time

state = {}


def channel(chop, name, default=0):
    channels = chop.chans(name) or chop.chans("/" + name)
    return float(channels[0][chop.numSamples - 1]) if channels and chop.numSamples else default


def onFrameStart(frame):
    features = me.parent()
    parent_comp = features.parent()
    source = parent_comp.op("NEON_INPUT/neon_osc")
    engine = parent_comp.op("FLUID_ENGINE")
    preset = parent_comp.par.Preset.eval()
    if preset != state.setdefault("preset", preset):
        state["preset"] = preset
        settings = json.loads(features.op("presets").text)[preset]
        for key in ("Force", "Swirl", "Drag", "Fade", "Iterations"):
            parent_comp.par[key].val = settings[key]
    now = time.monotonic()
    session, clock = channel(source, "session"), channel(source, "clock", -1)
    if session != state.get("session"):
        state.update(session=session, clock=None, blink=0, last=now,
                     seen=0, position=(.5, .5), wave=(.5, .5, 0))
    if clock != state["clock"]:
        state.update(clock=clock, seen=now)
    fresh = clock >= 0 and now - state["seen"] < .3
    valid = fresh and channel(source, "valid") == 1
    x, y = channel(source, "gx", .5), channel(source, "gy", .5)
    if valid:
        state["position"] = (x, y)
    blink = channel(source, "blink")
    if fresh and blink > state["blink"]:
        state["wave"] = (*state["position"], now)
    state["blink"] = blink
    wx, wy, when = state["wave"]
    age = now - when
    wave = (wx, wy, min(age, 2.0), math.exp(-7.0*age) if age < 1.2 else 0)
    dt = min(.034, max(.001, now - state["last"]))
    state["last"] = now
    radius = max(.012, min(.095, parent_comp.par.Radius.eval() + .022*channel(source, "pupil_delta")))
    dwell = channel(source, "dwell") if valid else 0
    motion = (channel(source, "vx"), channel(source, "vy"), dwell, dt)
    style = tuple(parent_comp.par[name].eval() for name in ("Force", "Swirl", "Drag", "Fade"))
    engine.op("pressure").par.npasses = int(parent_comp.par.Iterations.eval())
    params = features.op("parameters")
    params.store("vectors", ((x, y, int(valid), radius), motion, wave, style))
    params.cook(force=True)
    scene_frame = int(channel(source, "scene_frame", -1))
    recording = parent_comp.op("RECORDING")
    movie = recording.op("scene_movie")
    movie.par.index = max(0, scene_frame)
    recording.op("movie_clock").par.index = int(fresh and scene_frame >= 0 and bool(movie.par.file.eval()))
    if frame % 6 == 0:
        message = (f'Day 012 / Gaze Fluid\n'
                   f'OSC {int(parent_comp.par.Port.eval())} | {"receiving" if fresh else "waiting"} | valid {int(valid)}\n'
                   f'UV {x:.3f}, {y:.3f} | speed {channel(source,"speed"):.2f} | dwell {dwell:.2f}s\n'
                   f'Pupil L/R {channel(source,"pupil_l",-1):.2f} / {channel(source,"pupil_r",-1):.2f} mm\n'
                   f'Blink {int(blink)} | scene frame {scene_frame} | t {clock:.2f}s\n'
                   f'Pressure iterations {int(parent_comp.par.Iterations.eval())}')
        features.op("debug").par.text = message
    # Force the texture graph to advance even when no viewer is open.
    parent_comp.op("VISUAL_RENDER/out_picture").cook(force=True)
    path = parent_comp.par.Syncfile.eval()
    capture = recording.op("capture")
    if path and capture.par.record.eval():
        destination = Path(path)
        first = not destination.exists()
        try:
            with destination.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                if first:
                    writer.writerow(("td_frame", "monotonic_s", "session", "source_clock_s",
                                     "source_epoch_ns", "gaze_clock_s", "scene_frame", "valid", "blink"))
                epoch = sum(int(channel(source, f"epoch{i}")) << (16*i) for i in range(4))
                writer.writerow((absTime.frame, now, int(session), clock, epoch,
                                 channel(source, "gaze_t", -1), scene_frame, int(valid), int(blink)))
        except OSError as exc:
            if state.get("sync_error") != str(exc):
                print(f"Day 12 frame sync: {exc}")
                state["sync_error"] = str(exc)
    return
