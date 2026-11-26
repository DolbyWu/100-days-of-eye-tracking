from pathlib import Path
from time import monotonic
import numpy as np

worker=None
retry=scan=0.
previous=0.
values=[1.,0.]
def onCook(scriptOp):
    global worker,retry,scan,previous
    _=absTime.frame
    now=monotonic()
    if (worker is None or not worker.worker.is_alive()) and now>=retry:
        retry=now+3
        helper=Path(project.folder)/'scripts/hand-pose'
        if helper.is_file():
            worker=Hands(helper)
    lines=[]
    old=values[1]
    dt=min(.08,max(0,now-previous))
    previous=now
    if worker and worker.worker.is_alive():
        if now-scan>.04:
            frame=scriptOp.inputs[0].numpyArray(delayed=True)
            if frame is not None and frame.shape==(360,640,4):
                worker.submit(np.clip(frame[::-1]*255,0,255).astype('uint8').tobytes())
            scan=now
        stamp,hands=worker.latest
        if now-stamp<.25 and isinstance(hands,dict):
            for idx,side in enumerate(('left','right')):
                if side not in hands: continue
                h=np.asarray(hands[side])
                if min(h[[0,4,8,9],2])<.28: continue
                xy=h[:,:2]*[16/9,1]
                palm=np.linalg.norm(xy[0]-xy[9])
                if palm<.035:continue
                gap=np.clip((np.linalg.norm(xy[4]-xy[8])/palm-.10)/1.35,0,1)
                target=.65+gap*.94 if idx==0 else -115+230*gap
                values[idx]+=(target-values[idx])*(1-np.exp(-dt/.12))
                lines.append((('scale','rotate')[idx],[(1-h[k,0],h[k,1]) for k in (4,8)]))
    scriptOp.store('lines',lines)
    scriptOp.store('speed',(values[1]-old)/max(dt,.001))
    scriptOp.copyNumpyArray(np.array([[[values[0],values[1],0,1]]],np.float32))
    scriptOp.store('pose',tuple(values))
