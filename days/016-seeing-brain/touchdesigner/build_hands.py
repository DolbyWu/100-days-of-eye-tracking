def add_hands(r,folder):
    def source(name,code):
        s=r.create(textDAT,name)
        s.text=code
        return s
    cam=r.create(videodeviceinTOP,'hand_camera')
    cam.par.driver='avfoundation'
    for value,label in zip(cam.par.device.menuNames,cam.par.device.menuLabels):
        if 'macbook' in label.lower():
            cam.par.device=value
            break
    frame=r.create(resolutionTOP,'hand_frame')
    frame.inputConnectors[0].connect(cam)
    frame.par.outputresolution='custom'
    frame.par.resolutionw=640
    frame.par.resolutionh=360
    worker=(folder.parent/'014-reading-orbits/gestures.py').read_text().split('def display_hand')[0]
    worker=worker.replace("reply if isinstance(reply, list) else []","reply if isinstance(reply,dict) and 'error' not in reply else {}")
    h=r.create(scriptTOP,'hand_input')
    h.par.callbacks=source('hand_callbacks',worker+(folder/'touchdesigner/hand_input.py').read_text()).name
    h.par.format='rgba32float'
    h.inputConnectors[0].connect(frame)
    channels=r.create(toptoCHOP,'hand_transform')
    channels.par.top=h.name
    pivot=r.create(nullCOMP,'anatomy_transform')
    pivot.par.scale.expr="max(.1,op('hand_transform')['r'].eval())"
    pivot.par.ry.expr="op('hand_transform')['g'].eval()"
    for geo in r.children:
        if geo != pivot and isinstance(geo,geometryCOMP):
            geo.par.parentxformsrc='specify'
            geo.par.parentobject=pivot.path
    sample=r.create(resolutionTOP,'trail_colors')
    sample.inputConnectors[0].connect(r.op('with_history'))
    sample.par.outputresolution='custom'
    sample.par.resolutionw=320
    sample.par.resolutionh=180
    fx=r.create(scriptTOP,'hand_overlay')
    fx.par.callbacks=source('hand_overlay_callbacks',(folder/'touchdesigner/dashboard.py').read_text()+'\n'+(folder/'touchdesigner/hand_overlay.py').read_text()).name
    fx.inputConnectors[0].connect(sample)
    composite=r.create(glslTOP,'gesture_composite')
    composite.par.pixeldat=source('gesture_mix',(folder/'touchdesigner/camera_composite.glsl').read_text()).name
    for i,n in enumerate((r.op('with_history'),fx,cam)):composite.inputConnectors[i].connect(n)
    r.op('disclosure').inputConnectors[0].connect(composite)
