"""Add stereo sonification to the Day 12 point cloud in TouchDesigner."""
from pathlib import Path


def install_neural_audio(folder):
    component = op("/project1/day12_gaze_fluid")
    if component is None:
        raise RuntimeError("Open the Day 12 neural point cloud project first")
    visual = component.op("VISUAL_RENDER")
    cloud = visual.op("neural_cloud")
    source = visual.op("cloud_source")
    if cloud is None or source is None:
        raise RuntimeError("The Day 12 point cloud is missing")
    if component.op("SOUND") is not None:
        raise RuntimeError("The sound network is already installed")
    previous = source.text
    audio = component.create(baseCOMP,"SOUND")
    page = None
    try:
        page = component.appendCustomPage("Neural Sound")
        enabled = page.appendToggle("Soundenabled",label="Sound Enabled")[0]
        volume = page.appendFloat("Soundvolume",label="Sound Volume")[0]
        enabled.val = enabled.default = True
        volume.val = volume.default = .70
        volume.min,volume.max,volume.clampMin,volume.clampMax = 0,1,True,True

        clock = audio.create(audiooscillatorCHOP,"audio_clock")
        clock.par.amp = 0
        clock.par.timeslice = True
        callback = audio.create(textDAT,"synth_source")
        callback.text = (folder / "neural_audio_td.py").read_text(encoding="utf-8")
        synth = audio.create(scriptCHOP,"neural_synth")
        synth.par.callbacks = callback.name
        synth.par.timeslice = True
        synth.inputConnectors[0].connect(clock)
        output = audio.create(audiodeviceoutCHOP,"speakers")
        output.par.active = True
        output.inputConnectors[0].connect(synth)
        synth.nodeX, output.nodeX = 220,440
        source.text = (folder / "neural_cloud_td.py").read_text(encoding="utf-8")
        cloud.cook(force=True)
        synth.cook(force=True)
        output.cook(force=True)
        for item in (cloud,clock,synth,output):
            if item.errors():
                raise RuntimeError(f"{item.name}: {item.errors()}")
    except Exception:
        source.text = previous
        for name in ("Soundenabled","Soundvolume"):
            par = getattr(component.par,name,None)
            if par is not None:
                par.destroy()
        audio.destroy()
        raise
    return audio


install_neural_audio(Path(DAY12))
