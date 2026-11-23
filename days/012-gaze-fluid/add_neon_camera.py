"""Add an optional Neon scene background to the neural-hotspot variant."""


def add_neon_camera(comp, url, eye_inset_shader=None):
    visual = comp.op("VISUAL_RENDER")
    if visual.op("neon_scene"):
        camera = visual.op("neon_scene")
        comp.par.Cameraurl = url
        if eye_inset_shader:
            enable_eye_inset(visual, eye_inset_shader)
        return camera

    hot = visual.op("neural_composite")
    if hot is None:
        raise RuntimeError("Open the Neural Signals variant first.")

    page = comp.appendCustomPage("Neon Camera")
    page.appendStr("Cameraurl", label="Scene RTSP URL")[0].val = url
    page.appendToggle("Cameraenabled", label="Camera Background")[0].val = True

    camera = visual.create(videostreaminTOP, "neon_scene")
    camera.par.url.expr = "parent(2).par.Cameraurl"
    camera.par.active.expr = "parent(2).par.Cameraenabled"
    camera.par.play = True
    camera.nodeX, camera.nodeY = hot.nodeX, hot.nodeY - 290

    code = visual.create(textDAT, "camera_composite_source")
    code.text = """
out vec4 fragColor;
void main() {
    vec3 hotspots = texture(sTD2DInputs[0], vUV.st).rgb;
    vec3 scene = texture(sTD2DInputs[1], vUV.st).rgb * .50;
    vec3 combined = 1.0 - (1.0-hotspots)*(1.0-scene);
    fragColor = TDOutputSwizzle(vec4(combined, 1.0));
}
"""
    code.nodeX, code.nodeY = hot.nodeX + 200, hot.nodeY - 290
    blend = visual.create(glslTOP, "camera_composite")
    blend.par.glslversion = "glsl450"
    blend.par.pixeldat = code.name
    blend.inputConnectors[0].connect(hot)
    blend.inputConnectors[1].connect(camera)
    blend.nodeX, blend.nodeY = hot.nodeX + 200, hot.nodeY - 145

    switch = visual.create(switchTOP, "background_mode")
    switch.inputConnectors[0].connect(hot)
    switch.inputConnectors[1].connect(blend)
    switch.par.index.expr = "int(parent(2).par.Cameraenabled.eval())"
    switch.nodeX, switch.nodeY = hot.nodeX + 400, hot.nodeY - 145
    visual.op("out_picture").inputConnectors[0].connect(switch)
    if eye_inset_shader:
        enable_eye_inset(visual, eye_inset_shader)
    return camera


def enable_eye_inset(visual, shader):
    parameters = visual.op("neural_parameters")
    visual.op("camera_composite").inputConnectors[2].connect(parameters)
    visual.op("camera_composite_source").text = shader
    visual.parent().par.Cameraurl.label = "Eye RTSP URL"
    visual.parent().par.Cameraenabled.label = "Eye Inset and Gaze Overlay"


neon_scene = add_neon_camera(op("/project1/day12_gaze_fluid"), SCENE_RTSP, globals().get("EYE_INSET_SHADER"))
