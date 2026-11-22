"""Run in TouchDesigner Textport. Set DAY12 to this folder first."""
from pathlib import Path


def build(folder):
    project = op("/project1")
    if project.op("day12_gaze_fluid"):
        raise RuntimeError("Day 12 already exists in this project")
    patch = project.create(baseCOMP, "day12_gaze_fluid")

    def create(network, kind, name, *inputs):
        node = network.create(kind, name)
        siblings = [child for child in network.children if child != node]
        node.nodeX = (len(siblings) % 5) * 200
        node.nodeY = -(len(siblings) // 5) * 145
        for index, upstream in enumerate(inputs):
            node.inputConnectors[index].connect(upstream)
        return node

    def resolution(node, width, height):
        node.par.outputresolution = "custom"
        node.par.resolutionw = width
        node.par.resolutionh = height

    def pass_top(network, name, *inputs):
        dat = create(network, textDAT, name + "_pixel")
        dat.text = common + "\n" + (folder / "shaders" / (name + ".glsl")).read_text()
        top = create(network, glslTOP, name, *inputs)
        top.par.pixeldat = dat.name
        top.par.glslversion = "glsl450"
        top.par.format = "rgba32float"
        resolution(top, 256, 256)
        return top

    try:
        common = (folder / "shaders/common.glsl").read_text()
        controls = patch.appendCustomPage("Fluid")
        for name, value, low, high in (
            ("Port", 9012, 1, 65535), ("Iterations", 24, 1, 64),
            ("Outputwidth", 960, 64, 1280), ("Outputheight", 960, 64, 1280),
            ("Force", 210, 0, 500), ("Swirl", 95, 0, 300),
            ("Drag", .38, 0, 3), ("Fade", .47, 0, 3),
            ("Radius", .038, .012, .095),
        ):
            add = controls.appendInt if isinstance(value, int) else controls.appendFloat
            par = add(name)[0]
            par.min, par.max, par.clampMin, par.clampMax = low, high, True, True
            par.default = value
            par.val = value
        from json import loads
        choices = loads((folder / "presets.json").read_text())
        preset = controls.appendMenu("Preset")[0]
        preset.menuNames = list(choices)
        preset.menuLabels = [item["label"] for item in choices.values()]
        preset.val = "filaments"
        neon, features, engine, visual, recording = [
            create(patch, baseCOMP, name) for name in
            ("NEON_INPUT", "GAZE_FEATURES", "FLUID_ENGINE", "VISUAL_RENDER", "RECORDING")
        ]
        osc = create(neon, oscinCHOP, "neon_osc")
        osc.par.port.expr = "parent(2).par.Port"
        osc.par.queued = False
        seed = create(engine, constantTOP, "zero")
        resolution(seed, 256, 256)
        seed.par.format = "rgba32float"
        seed.par.colorr = seed.par.colorg = seed.par.colorb = 0
        buffers = [create(engine, feedbackTOP, name, seed)
                   for name in ("velocity_history", "pressure_history", "dye_history")]
        params_dat = create(features, textDAT, "parameter_pixels")
        params_dat.text = (folder / "parameters_td.py").read_text()
        params = create(features, scriptTOP, "parameters")
        params.par.callbacks = params_dat.name
        params.par.format = "rgba32float"
        param_in = create(engine, selectTOP, "parameters")
        param_in.par.top.expr = "parent(2).op('GAZE_FEATURES/parameters')"
        velocity = pass_top(engine, "velocity", buffers[0], param_in)
        div = pass_top(engine, "divergence", velocity)
        pressure = pass_top(engine, "pressure", buffers[1], div)
        pressure.par.npasses = 24
        projected = pass_top(engine, "project", velocity, pressure)
        dye = pass_top(engine, "dye", buffers[2], projected, param_in)
        for buffer, target in zip(buffers, (projected, pressure, dye)):
            buffer.par.top = target.name
            buffer.par.resetpulse.pulse()

        dye_in = create(visual, selectTOP, "dye_in")
        dye_in.par.top.expr = "parent(2).op('FLUID_ENGINE/dye')"
        render = pass_top(visual, "render", dye_in)
        render.par.resolutionw.expr = "parent(2).par.Outputwidth"
        render.par.resolutionh.expr = "parent(2).par.Outputheight"
        picture = create(visual, outTOP, "out_picture", render)
        picture.viewer = True
        create(patch, outTOP, "out_picture", visual)
        debug = create(features, textTOP, "debug")
        resolution(debug, 640, 360)
        tick = create(features, executeDAT, "drive")
        tick.text = (folder / "drive_td.py").read_text()

        movie = create(recording, moviefileinTOP, "scene_movie")
        movie.par.file = ""
        movie.par.playmode = "specify"
        movie.par.indexunit = "indices"
        movie.par.interp = False
        black = create(recording, constantTOP, "no_scene")
        black.par.colorr = black.par.colorg = black.par.colorb = 0
        clocked = create(recording, switchTOP, "movie_clock", black, movie)
        create(recording, outTOP, "out_scene", clocked)
        output = create(recording, selectTOP, "fluid_output")
        output.par.top.expr = "parent(2).op('VISUAL_RENDER/out_picture')"
        create(recording, moviefileoutTOP, "capture", output)
        presets = create(features, textDAT, "presets")
        presets.text = (folder / "presets.json").read_text()
        controls.appendFile("Syncfile", label="Frame sync CSV")[0].val = ""
        tick.par.framestart = True
        print("Created", patch.path)
        return patch
    except Exception:
        patch.destroy()
        raise


day12 = build(Path(DAY12))
