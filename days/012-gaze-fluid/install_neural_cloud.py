"""Run in the Day 12 TouchDesigner Textport. Pass DAY12 and DAY12_CLOUD."""
from pathlib import Path


def install_cloud(folder, asset):
    comp = op("/project1/day12_gaze_fluid")
    if comp is None:
        raise RuntimeError("Open the Day 12 Eye Inset project first")
    visual = comp.op("VISUAL_RENDER")
    switch = visual.op("background_mode")
    art = visual.op("neural_background")
    art_path = (folder / "media" / "neural-background.jpg").resolve()
    if switch is None or art is None or not asset.is_file() or not art_path.is_file():
        raise RuntimeError("The Eye Inset project, reference image, or exported PLY is missing")
    if visual.op("surface_eye_overlay") is None:
        installer = folder / "install_surface_eye_overlay.py"
        exec(compile(installer.read_text(), str(installer), "exec"),
             dict(globals(), DAY12=str(folder)))
    eye = visual.op("surface_eye_overlay")
    eye_code = visual.op("surface_eye_overlay_source")
    original_inputs = tuple(switch.inputs)
    original_eye_input = eye.inputs[0]
    original_eye_shader = eye_code.text
    original_art_file = art.par.file.val
    shader = (folder / "shaders/eye_live_overlay.glsl").read_text()
    callback = (folder / "neural_cloud_td.py").read_text()
    finish_shader = (folder / "shaders/cloud_finish.glsl").read_text()
    created, saved = [], []

    def node(kind, name):
        existing = visual.op(name)
        if existing is not None:
            return existing
        result = visual.create(kind, name)
        created.append(result)
        return result

    try:
        source = node(textDAT, "cloud_source")
        path = node(textDAT, "cloud_asset_path")
        finish_source = node(textDAT, "cloud_finish_source")
        saved = [(source, source.text),(path,path.text),(finish_source,finish_source.text)]
        source.text, path.text = callback, str(asset)
        finish_source.text = finish_shader
        cloud = node(scriptTOP, "neural_cloud")
        cloud.par.callbacks = source.name
        cloud.par.format = "rgba8fixed"
        cloud.inputConnectors[0].connect(visual.op("neural_parameters"))
        cloud.nodeX, cloud.nodeY = eye.nodeX-220, eye.nodeY+180
        cloud.cook(force=True)
        problems = cloud.errors()
        if problems or (cloud.width,cloud.height) != (1200,815):
            raise RuntimeError(f"Cloud render failed: {problems}")
        finish = node(glslTOP, "cloud_finish")
        finish.par.glslversion = "glsl450"
        finish.par.pixeldat = finish_source.name
        finish.inputConnectors[0].connect(cloud)
        art.par.file = str(art_path)
        finish.inputConnectors[1].connect(art)
        finish.cook(force=True)
        if finish.errors():
            raise RuntimeError(finish.errors())
        eye_code.text = shader
        eye.inputConnectors[0].connect(finish)
        switch.inputConnectors[0].connect(finish)
        switch.inputConnectors[1].connect(eye)
        comp.par.Cameraenabled = True
        eye.cook(force=True)
        if eye.errors():
            raise RuntimeError(eye.errors())
    except Exception:
        eye_code.text = original_eye_shader
        art.par.file = original_art_file
        eye.inputConnectors[0].connect(original_eye_input)
        for connector, old in zip(switch.inputConnectors, original_inputs):
            connector.connect(old)
        for item, value in saved:
            item.text = value
        for item in reversed(created):
            item.destroy()
        raise
    print("Day 12 point cloud installed. View /project1/day12_gaze_fluid/out_picture.")
    return cloud


install_cloud(Path(DAY12), Path(DAY12_CLOUD))
