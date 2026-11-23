"""Run once in TouchDesigner Textport on the working Day12 Eye Inset project.

Set DAY12 to this directory, then exec this file. Nothing is saved automatically.
"""
from pathlib import Path


def install(folder):
    comp=op('/project1/day12_gaze_fluid')
    if comp is None:
        raise RuntimeError('Open Day12-Recovery-Eye-Inset.toe first')
    visual=comp.op('VISUAL_RENDER')
    camera=visual.op('camera_composite')
    source=visual.op('camera_composite_source')
    if camera is None or source is None:
        raise RuntimeError('The working Eye Inset camera layer is missing')
    # A failed or interrupted Textport run can leave some of these nodes behind.
    # Restore the original camera path, then remove only this installer's nodes.
    switch=visual.op('background_mode')
    if switch is None:
        raise RuntimeError('The Eye Inset background switch is missing')
    switch.inputConnectors[1].connect(camera)
    for name in ('surface_eye_overlay', 'surface_eye_overlay_source',
                 'surface_markers', 'eye_parameters', 'eye_parameters_source',
                 'camera_composite_before_surface'):
        stale=visual.op(name)
        if stale is not None:
            stale.destroy()
    marker_image=folder/'media'/'surface-markers.png'
    shader=folder/'shaders'/'eye_live_overlay.glsl'
    callback=folder/'eye_parameters_td.py'
    for path in (marker_image,shader,callback):
        if not path.is_file():
            raise FileNotFoundError(path)
    created=[]
    try:
        code=visual.create(textDAT,'eye_parameters_source')
        created.append(code)
        code.text=callback.read_text(encoding='utf-8')
        code.nodeX,code.nodeY=visual.op('neural_parameters').nodeX+200,visual.op('neural_parameters').nodeY-180
        eye=visual.create(scriptTOP,'eye_parameters')
        created.append(eye)
        eye.par.callbacks=code.name
        eye.par.format='rgba32float'
        eye.nodeX,eye.nodeY=code.nodeX+180,code.nodeY
        marker=visual.create(moviefileinTOP,'surface_markers')
        created.append(marker)
        marker.par.file=str(marker_image)
        marker.par.play=False
        marker.nodeX,marker.nodeY=eye.nodeX,eye.nodeY-150
        # The regular GLSL TOP has only three inputs. Keep it intact and
        # insert a GLSL Multi TOP for the five-input eye overlay.
        overlay_source=visual.create(textDAT,'surface_eye_overlay_source')
        created.append(overlay_source)
        overlay_source.text=shader.read_text(encoding='utf-8')
        overlay=visual.create(glslmultiTOP,'surface_eye_overlay')
        created.append(overlay)
        overlay.par.glslversion='glsl450'
        overlay.par.pixeldat=overlay_source.name
        for index, upstream in enumerate((visual.op('neural_composite'), visual.op('neon_scene'), visual.op('neural_parameters'), eye, marker)):
            if upstream is None:
                raise RuntimeError('Missing input for eye overlay: ' + str(index))
            overlay.inputConnectors[index].connect(upstream)
        overlay.nodeX,overlay.nodeY=camera.nodeX+200,camera.nodeY-170
        switch.inputConnectors[1].connect(overlay)
        comp.par.Cameraenabled=True
        print('Installed AprilTag display and live eye annotations. View VISUAL_RENDER/out_picture.')
        print('Inspect surface_eye_overlay Info DAT for GLSL errors before saving a new .toe.')
    except Exception:
        switch.inputConnectors[1].connect(camera)
        for item in reversed(created):
            item.destroy()
        raise


install(Path(DAY12))
