import json
from pathlib import Path
from time import monotonic
engine=None
def onCook(scriptOp):
    global engine
    _=absTime.frame
    root=scriptOp.parent()
    if engine is None:
        engine=Signals(json.loads(root.op('mapping').text))
    t=monotonic()
    if root.par.Mock:
        packet=demo(absTime.seconds)
    else:
        osc=root.op('neon')
        packet={k:(osc[k].eval() if osc[k] is not None else None)
                for k in ('session','gaze_t','valid','gx','gy','blink','pupil_l','pupil_r')}
        words=[osc['epoch'+str(i)] for i in range(4)]
        if all(c is not None for c in words) and packet['gaze_t'] is not None:
            epoch=sum((int(c.eval()) & 65535) << (16*i) for i,c in enumerate(words))
            scriptOp.store('source_gaze_ns',epoch+round(packet['gaze_t']*1e9))
    event,until=root.fetch('trigger',('',0))
    levels=engine.step(packet,t,event if t<until else '')
    scriptOp.clear()
    for k in ('V1','SC','LGN','FEF','IPS','MT_MST','cerebellum','brainstem'):
        val=levels.get(k,0)
        for name in (['activation_'+k+'_'+s for s in 'LR'] if k.isupper() else ['activation_'+k]):
            scriptOp.appendChan(name)[0]=val
    for k,v in zip(('look_x','look_y','dilation','flow'),(*engine.direction,engine.pupil,
            0 if (event if t<until else engine.event) in ('','blink') or t<engine.flash_until else .18+.65*levels.get('FEF',0)+.25*levels.get('V1',0))):
        scriptOp.appendChan(k)[0]=v
