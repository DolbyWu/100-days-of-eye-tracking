"""Run in TouchDesigner Textport after install_surface_eye_overlay.py.

Creates a dedicated two-input image compositing pass. It deliberately does not
rely on the eye shader to carry the calibration tag alpha.
"""
from pathlib import Path


def install(folder):
    visual = op('/project1/day12_gaze_fluid/VISUAL_RENDER')
    if visual is None:
        raise RuntimeError('Open Day12-Recovery-Eye-Inset.toe first')
    switch = visual.op('background_mode')
    eye = visual.op('surface_eye_overlay')
    marker = visual.op('surface_markers')
    if switch is None or eye is None or marker is None:
        raise RuntimeError('Run install_surface_eye_overlay.py first')
    for name in ('visible_markers', 'visible_markers_source'):
        old = visual.op(name)
        if old is not None:
            old.destroy()
    source = visual.create(textDAT, 'visible_markers_source')
    source.text = '''
out vec4 fragColor;
void main(){
    vec4 base=texture(sTD2DInputs[0],vUV.st);
    vec4 tag=texture(sTD2DInputs[1],vUV.st);
    fragColor=TDOutputSwizzle(vec4(mix(base.rgb,tag.rgb,tag.a),1.));
}
'''
    overlay = visual.create(glslTOP, 'visible_markers')
    overlay.par.glslversion = 'glsl450'
    overlay.par.pixeldat = source.name
    overlay.inputConnectors[0].connect(eye)
    overlay.inputConnectors[1].connect(marker)
    overlay.nodeX, overlay.nodeY = eye.nodeX + 210, eye.nodeY - 130
    switch.inputConnectors[1].connect(overlay)
    print('Visible calibration markers installed. Four black-and-white squares should now be visible.')


install(Path(DAY12))
