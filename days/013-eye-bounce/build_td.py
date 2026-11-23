from pathlib import Path

folder = Path(DAY13)
project_root = op('/project1')
if project_root.op('day13_eye_bounce'):
    raise RuntimeError('Day 13 already exists in this project')
root = project_root.create(baseCOMP,'day13_eye_bounce')

def node(kind,name,x,y):
    item=root.create(kind,name)
    item.nodeX,item.nodeY=x,y
    return item

def resolution(item,width,height):
    item.par.outputresolution='custom'
    item.par.resolutionw=width
    item.par.resolutionh=height

try:
    page=root.appendCustomPage('Eye Bounce')
    for name,label,default in (
        ('Demo','Simulated Gaze and Hand',True),('Webcam','Mac Camera',False),
        ('Hands','Hand Collision',True),('Mirror','Mirror Camera and Gaze',True),
        ('Manualeye','Manual Eye Video URL',False),
    ):
        p=page.appendToggle(name,label=label)[0]
        p.default=p.val=default
    page.appendStr('Liveeye',label='Neon Eye RTSP URL')
    port=page.appendInt('Port',label='OSC Port')[0]
    port.default=port.val=9012
    webcam=node(videodeviceinTOP,'mac_camera',0,0)
    webcam.par.driver='avfoundation'
    webcam.par.active.expr='bool(parent().par.Webcam.eval() and not parent().par.Demo.eval())'
    hand_frame=node(resolutionTOP,'hand_frame',190,0)
    hand_frame.inputConnectors[0].connect(webcam)
    resolution(hand_frame,640,360)
    eyes=node(videostreaminTOP,'neon_eyes',0,-145)
    eyes.par.url.expr='parent().par.Liveeye.eval()'
    eyes.par.active.expr='bool(parent().par.Liveeye.eval() and not parent().par.Demo.eval())'
    eyes.par.play=True
    osc=node(oscinCHOP,'neon_osc',0,-300)
    osc.par.port.expr='parent().par.Port.eval()'
    osc.par.queued=False
    source=node(textDAT,'motion_source',180,-300)
    source.text=(folder/'motion.py').read_text()
    motion=node(scriptTOP,'motion',370,-300)
    motion.par.callbacks=source.name
    motion.par.format='rgba32float'
    code=node(textDAT,'eye_shader',370,0)
    code.text=(folder/'eye_bounce.glsl').read_text()
    render=node(glslTOP,'eye_bounce',575,-145)
    render.par.glslversion='glsl450'
    render.par.pixeldat=code.name
    resolution(render,1280,720)
    for index,input_op in enumerate((webcam, eyes, motion)):
        render.inputConnectors[index].connect(input_op)
    output=node(outTOP,'out_picture',770,-145)
    output.inputConnectors[0].connect(render)
    output.viewer=True
    output.cook(force=True)
    for item in (motion,render,output):
        if item.errors():
            raise RuntimeError(f'{item.path}: {item.errors()}')
    print('Day 13 ready:',output.path)
except Exception:
    root.destroy()
    raise
