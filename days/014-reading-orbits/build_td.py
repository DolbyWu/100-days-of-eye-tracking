from pathlib import Path

def build(folder):
    folder=Path(folder)
    base=op('/project1')
    if base.op('day14_reading'): raise ValueError('Day 14 already exists')
    r=base.create(baseCOMP,'day14_reading')
    def node(kind,name,x,y):
        n=r.create(kind,name)
        n.nodeX,n.nodeY=x,y
        return n
    def size(n,w,h):
        n.par.outputresolution='custom'
        n.par.resolutionw=w
        n.par.resolutionh=h
    def text(name,value,x,y):
        n=node(textDAT,name,x,y)
        n.text=value
        return n
    def connect(n,i,source): n.inputConnectors[i].connect(source)
    p=r.appendCustomPage('Reading')
    for name,label,default in [('Demo','Demo Book',False),('Webcam','Mac Camera',True)]:
        par=p.appendToggle(name,label=label)[0]
        par.default=par.val=default
    menu=p.appendMenu('Reader',label='Page Recognition')[0]
    menu.menuNames=['Local','OpenAI']
    menu.menuLabels=['Apple Vision (local)','OpenAI (one image per scan)']
    p.appendPulse('Enterkey',label='Enter API Key')
    p.appendPulse('Importpage',label='Import Photo or PDF')
    p.appendPulse('Resetreading',label='Reset Reading')
    p.appendPulse('Scan',label='Scan Page')
    p.appendToggle('Autopages',label='Auto Scan New Pages')
    p.appendStr('Status',label='Reading Status')
    ports=r.appendCustomPage('Cameras')
    for name,label in [('Autoeye','Eye URL from Bridge'),('Autoscene','Derive Scene URL')]:
        par=ports.appendToggle(name,label=label)[0]
        par.default=par.val=True
    ports.appendStr('Neonhost',label='Companion IP (optional)')
    ports.appendStr('Eyeurl',label='Eye RTSP')
    ports.appendStr('Sceneurl',label='Scene RTSP')
    port=ports.appendInt('Port',label='OSC Port')[0]
    port.default=port.val=9000
    cam=node(videodeviceinTOP,'mac_camera',0,100)
    cam.par.driver='avfoundation'
    cam.par.active.expr='bool(parent().par.Webcam and not parent().par.Demo)'
    for value,label in zip(cam.par.device.menuNames,cam.par.device.menuLabels):
        if 'macbook' in label.lower():
            cam.par.device=value
            break
    hand=node(resolutionTOP,'hand_frame',180,100)
    size(hand,640,360)
    connect(hand,0,cam)
    for name,par,y in [('neon_eyes','Eyeurl',-40),('book_camera','Sceneurl',-180)]:
        n=node(videostreaminTOP,name,0,y)
        n.par.url.expr=f'parent().par.{par}.eval()'
        n.par.active.expr=f'bool(parent().par.{par}.eval() and not parent().par.Demo.eval())'
        n.par.play=True
    osc=node(oscinCHOP,'neon_osc',0,-320)
    osc.par.port.expr='parent().par.Port.eval()'
    osc.par.queued=False
    source=text('reading_source','\n'.join((folder/f).read_text() for f in
                ['figures.py','reading.py','gestures.py','runtime.py']),200,-300)
    m=node(scriptTOP,'interaction',400,30)
    m.par.callbacks=source.name
    m.par.format='rgba32float'
    mask=text('word_source',(folder/'overlay.py').read_text(),400,-300)
    words=node(scriptTOP,'floating_words',600,30)
    words.par.callbacks=mask.name
    connect(words,0,m)
    shader=text('portrait_shader',(folder/'render.glsl').read_text(),620,-300)
    view=node(glslTOP,'portrait',800,30)
    view.par.glslversion='glsl450'
    view.par.pixeldat=shader.name
    size(view,1280,720)
    for i,n in enumerate((cam,r.op('neon_eyes'),m)): connect(view,i,n)
    ink_shader=text('ink_shader',(folder/'ink.glsl').read_text(),820,-300)
    ink=node(glslTOP,'composite_words',1000,30)
    ink.par.glslversion='glsl450'
    ink.par.pixeldat=ink_shader.name
    for i,n in enumerate((view,words,m)): connect(ink,i,n)
    out=node(outTOP,'out_picture',1200,30)
    connect(out,0,ink)
    out.viewer=True
    ctl=node(parameterexecuteDAT,'reading_controls',200,-460)
    ctl.par.op='..'
    ctl.par.pars='Enterkey Scan Importpage Resetreading'
    ctl.par.onpulse=True
    ctl.text="""def onPulse(par):
    parent().op('reading_source').module.action(par.name)
    return
"""
    startup=node(executeDAT,'open_reading',400,-460)
    startup.par.start=True
    startup.text="""def onStart():
    run("args[0].op('out_picture').openViewer(); args[0].openParameters()", parent(), delayFrames=12)
    return
"""
    r.nodeX,r.nodeY=0,0
    r.current=True
    r.selected=True
    return r
