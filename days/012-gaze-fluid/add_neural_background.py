"""Apply the neural artwork layer to an existing Day 12 patch in Textport."""
from pathlib import Path


def add_neural_background(comp, folder):
    visual = comp.op("VISUAL_RENDER")
    if visual.op("neural_composite"):
        return visual.op("neural_composite")
    art_path = folder / "media" / "neural-background.jpg"
    shader_path = folder / "shaders"
    shader = (shader_path / "common.glsl").read_text() + "\n"
    shader += (shader_path / "neural_composite.glsl").read_text()
    if not art_path.is_file():
        raise FileNotFoundError(art_path)

    fluid = visual.op("render")
    art = visual.create(moviefileinTOP, "neural_background")
    art.par.file = str(art_path)
    art.nodeX, art.nodeY = fluid.nodeX - 200, fluid.nodeY - 280
    source = visual.create(textDAT, "neural_composite_source")
    source.text = shader
    source.nodeX, source.nodeY = fluid.nodeX, fluid.nodeY - 280
    composite = visual.create(glslTOP, "neural_composite")
    composite.par.pixeldat = source.name
    composite.par.glslversion = "glsl450"
    composite.par.outputresolution = "useinput"
    composite.nodeX, composite.nodeY = fluid.nodeX + 200, fluid.nodeY - 145
    parameters = visual.create(selectTOP, "neural_parameters")
    parameters.par.top.expr = "parent(2).op('GAZE_FEATURES/parameters')"
    parameters.nodeX, parameters.nodeY = art.nodeX, art.nodeY - 145
    composite.inputConnectors[0].connect(fluid)
    composite.inputConnectors[1].connect(art)
    composite.inputConnectors[2].connect(parameters)
    visual.op("out_picture").inputConnectors[0].connect(composite)
    comp.par.Outputwidth = 1200
    comp.par.Outputheight = 815
    return composite


neural_composite = add_neural_background(op("/project1/day12_gaze_fluid"), Path(DAY12))
