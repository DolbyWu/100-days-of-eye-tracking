"""In a new TD project, call build(Path('/absolute/path/to/017-seeing-brain'))."""
import json
from pathlib import Path

def build(folder):
    folder=Path(folder).resolve()
    meta=json.loads((folder/'assets/manifest.json').read_text())['objects']
    host=op('/project1')
    if host.op('seeing_brain'): raise RuntimeError('Open a fresh project before building.')
    root=host.create(baseCOMP,'seeing_brain')
    def node(kind,name):
        return root.create(kind,name)
    def text(name,content):
        n=node(textDAT,name)
        n.text=content
        return n
    def control(page,kind,name,default,low=None,high=None):
        p=getattr(page,'append'+kind)(name)[0]
        p.default=p.val=default
        if low is not None:
            p.min=p.normMin=low
            p.max=p.normMax=high
            p.clampMin=p.clampMax=True
        return p
    page=root.appendCustomPage('Seeing Brain')
    control(page,'Toggle','Mock',True)
    control(page,'Int','Port',9000,1,65535)
    control(page,'Float','Azimuth',32,-180,180)
    control(page,'Float','Elevation',8,-89,89)
    control(page,'Float','Skull',.38,0,1)
    control(page,'Float','Brain',.36,0,1)
    control(page,'Float','Exposure',2.7,.1,6)
    control(page,'Float','Bloom',.28,0,1)
    control(page,'Toggle','Reduced',False)
    control(page,'Int','Particles',28,1,128)
    control(page,'Int','Width',960,320,1920)
    control(page,'Toggle','Growth',False)
    control(page,'Int','Agents',220,8,1500)
    for name,default,low,high in [('Sensor',.55,.1,1.5),('Distance',3,1,12),('Deposit',.07,.001,.3),('Diffusion',.24,0,1),('Retention',.975,.7,.999),('Attraction',.4,0,3)]:
        control(page,'Float',name,default,low,high)
    control(page,'Toggle','Record',False)
    for name in ('Fixation','Saccade','Blink','Reset'):page.appendPulse(name)
    ctl=node(parameterexecuteDAT,'manual_controls')
    ctl.par.op='..'
    ctl.par.pars='Fixation Saccade Blink Reset'
    ctl.par.onpulse=True
    ctl.text="""from time import monotonic
def onPulse(par):
    root=parent()
    if par.name=='Reset':
        mod=root.op('features_source').module
        if mod.engine: mod.engine.reset()
        root.store('generation',root.fetch('generation',0)+1)
        root.store('trigger',('',0))
    else:
        root.store('trigger',(par.name.lower(),monotonic()+.65))
"""
    text('mapping',(folder/'config/activation.json').read_text())
    text('landmarks',json.dumps({k:v['center'] for k,v in meta.items()}))
    osc=node(oscinCHOP,'neon')
    osc.par.port.expr='parent().par.Port.eval()'
    osc.par.active.expr='not parent().par.Mock.eval()'
    source=text('features_source',(folder/'src/signals.py').read_text()+'\n'+(folder/'touchdesigner/features.py').read_text())
    features=node(scriptCHOP,'features')
    features.par.callbacks=source.name
    path_cb=text('pathway_source',(folder/'touchdesigner/pathways.py').read_text())
    inst=node(scriptCHOP,'pulse_positions')
    inst.par.callbacks=path_cb.name
    page=root.appendCustomPage('Region gain')
    manual_regions=root.appendCustomPage('Manual emission')
    camera=node(cameraCOMP,'orbit')
    camera.par.projection='ortho'
    camera.par.orthowidth=4.5
    camera.par.ry.expr='parent().par.Azimuth.eval()'
    camera.par.rx.expr='-parent().par.Elevation.eval()'
    camera.par.tx.expr='4*math.sin(math.radians(me.par.ry))*math.cos(math.radians(me.par.rx))'
    camera.par.ty.expr='-4*math.sin(math.radians(me.par.rx))'
    camera.par.tz.expr='4*math.cos(math.radians(me.par.ry))*math.cos(math.radians(me.par.rx))'
    light=node(lightCOMP,'key_light')
    light.par.tx=-2
    light.par.ty=4
    light.par.tz=4
    fill=node(lightCOMP,'rim_light')
    fill.par.tx=3
    fill.par.ty=2
    fill.par.tz=-2
    layers=[[],[],[]]
    for key in list(meta)+['pulses']:
        geo=node(geometryCOMP,key)
        for child in geo.children:
            if child.family in ('SOP','POP'):child.destroy()
        if key=='pulses':
            mesh=geo.create(sphereSOP,'spark')
            mesh.par.radx=mesh.par.rady=mesh.par.radz=.009
            geo.par.instancing=True
            geo.par.instanceop=inst.path
            for axis in 'xyz':getattr(geo.par,'instancet'+axis).val=axis
        else:
            mesh=geo.create(fileinSOP,'surface')
            mesh.par.file.expr=f"project.folder+'/assets/meshes/{key}.obj' if __import__('os').path.exists(project.folder+'/assets/manifest.json') else {str(folder/'assets/meshes'/(key+'.obj'))!r}"
        mesh.display=mesh.render=True
        mat=node(phongMAT,'mat_'+key)
        geo.par.material=mat.path
        if key=='skull':layer=0;color=(.45,.76,.95)
        elif key.startswith('brain_'):layer=1;color=(.45,.56,.64)
        elif key.startswith('eye_'):layer=2;color=(.30,.44,.47)
        elif key.startswith('iris_'):layer=2;color=(.04,.17,.21)
        elif key.startswith('tract') or key=='chiasm':layer=2;color=(.10,.17,.20)
        else:layer=2;color=(.11,.075,.055)
        layers[layer].append(geo.name)
        for axis,value in zip('rgb',color):getattr(mat.par,'diff'+axis).val=value
        if key.startswith(('iris_','eye_')):
            pivot=meta['eye_'+key[-1]]['center']
            for axis,v in zip('xyz',pivot):getattr(geo.par,'p'+axis).val=v
            geo.par.ry.expr="14*op('features')['look_x']"
            geo.par.rx.expr="-10*op('features')['look_y']"
        elif key=='pulses':
            for axis,v in zip('rgb',(1,.40,.095)):
                getattr(mat.par,'emit'+axis).expr=f"{v}*op('features')['flow']"
            for axis in 'rgb':getattr(mat.par,'diff'+axis).val=0
        elif layer==2 and key not in ('chiasm','tract_L','tract_R'):
            gain=control(page,'Float','Gain'+key.replace('_','').lower(),1,0,3)
            floor=control(manual_regions,'Float','Emit'+key.replace('_','').lower(),0,0,1)
            for axis,v in zip('rgb',(1,.31,.055)):
                getattr(mat.par,'emit'+axis).expr=f"{v}*parent().par.{gain.name}*max(parent().par.{floor.name}.eval(),op('features')['activation_{key}'].eval())*(1-.50*int(parent().par.Reduced))"
    passes=[]
    for names,label in zip(layers,('skull','cortex','activity')):
        r=node(renderTOP,'render_'+label)
        r.par.camera=camera.name
        r.par.geometry=' '.join(names)
        r.par.lights='key_light rim_light'
        r.par.outputresolution='custom'
        r.par.resolutionw.expr='parent().par.Width.eval()'
        r.par.resolutionh.expr='round(parent().par.Width.eval()*9/16)'
        passes.append(r)
    code=text('composite_shader',(folder/'touchdesigner/composite.glsl').read_text())
    composite=node(glslTOP,'scan')
    composite.par.pixeldat=code.name
    composite.par.vec=2
    for i,(label,pars) in enumerate([('levels',['Skull','Brain','Exposure']),('optics',['Bloom'])]):
        getattr(composite.par,'vec'+str(i)+'name').val=label
        for axis,par in zip('xyzw',pars):getattr(composite.par,'vec'+str(i)+'value'+axis).expr='parent().par.'+par+'.eval()'
    composite.par.vec0valuew.expr="op('features')['dilation'].eval()"
    for i,r in enumerate(passes):composite.inputConnectors[i].connect(r)
    small=[]
    for label,source in zip(('cortex','activity'),passes[1:]):
        n=node(resolutionTOP,'sample_'+label)
        n.inputConnectors[0].connect(source)
        n.par.outputresolution='custom'
        n.par.resolutionw=160
        n.par.resolutionh=90
        small.append(n)
    gc=text('growth_source',(folder/'touchdesigner/growth.py').read_text())
    growth=node(scriptTOP,'projected_growth')
    growth.par.callbacks=gc.name
    growth.par.format='rgba32float'
    for i,n in enumerate(small):growth.inputConnectors[i].connect(n)
    final_shader=text('history_shader','out vec4 fragColor; void main(){vec2 uv=vUV.st; fragColor=TDOutputSwizzle(vec4(texture(sTD2DInputs[0],uv).rgb+texture(sTD2DInputs[1],uv).rgb,1.));}')
    final=node(glslTOP,'with_history')
    final.par.pixeldat=final_shader.name
    for i,n in enumerate((composite,growth)):final.inputConnectors[i].connect(n)
    caption=node(textTOP,'disclosure')
    caption.inputConnectors[0].connect(final)
    caption.par.text='Neuroscience-informed simulation · Not measured brain activity'
    caption.par.fontsizex=13
    caption.par.aligny='bottom'
    caption.par.fontcolorr=.63
    caption.par.fontcolorg=.74
    caption.par.fontcolorb=.79
    out=node(outTOP,'out_scan')
    out.inputConnectors[0].connect(caption)
    out.display=out.viewer=True
    movie=node(moviefileoutTOP,'record_scan')
    movie.inputConnectors[0].connect(out)
    movie.par.record=False
    ctl.par.pars='Fixation Saccade Blink Reset Record'
    ctl.par.valuechange=True
    ctl.text+="""
def onValueChange(par,prev):
    if par.name=='Record':
        movie=parent().op('record_scan')
        if par.eval():
            from time import time_ns
            movie.par.file=project.folder+'/scan-'+str(time_ns())+'.mov'
        movie.par.record=bool(par.eval())
"""
    for i,n in enumerate(root.children):
        n.nodeX=(i%9)*195
        n.nodeY=-(i//9)*145
    hand_scope=globals().copy()
    exec((folder/"touchdesigner/build_hands.py").read_text(),hand_scope)
    hand_scope["add_hands"](root,folder)
    root.par.opviewer=out.path
    return root
