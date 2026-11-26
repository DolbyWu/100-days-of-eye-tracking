"""Projected, cortex-constrained trail history. One vectorized update per step."""
import numpy as np
import cv2
from time import monotonic
rng=np.random.default_rng(17)
trail=np.zeros((90,160),np.float32)
positions=np.empty((0,2))
heading=np.empty(0)
last=-1.
key=None
def onCook(scriptOp):
    global positions,heading,last,key
    _=absTime.frame
    r=scriptOp.parent()
    now=monotonic()
    state=(r.par.Azimuth.eval(),r.par.Elevation.eval(),int(r.par.Agents),r.fetch('generation',0),bool(r.par.Growth))
    if key!=state:
        key=state
        trail.fill(0)
        positions=np.empty((0,2))
    if r.par.Growth and now-last>=1/32:
        last=now
        cortex=scriptOp.inputs[0].numpyArray(delayed=True)
        activity=scriptOp.inputs[1].numpyArray(delayed=True)
        if cortex is not None and activity is not None:
            mask=cv2.resize(cortex[:,:,:3].max(2),(160,90))>.035
            allowed=np.argwhere(mask)
            if len(allowed):
                count=int(r.par.Agents)
                if len(positions)!=count:
                    positions=allowed[rng.integers(len(allowed),size=count)][:,::-1].astype(float)
                    heading=rng.uniform(-np.pi,np.pi,count)
                red=cv2.resize(activity[:,:,0],(160,90))
                field=trail+float(r.par.Attraction)*cv2.GaussianBlur(red,(0,0),2)
                def move(a,dist):
                    return np.clip(positions+dist*np.column_stack((np.cos(a),np.sin(a))),[0,0],[159,89])
                def sense(a):
                    x,y=move(a,float(r.par.Distance)).astype(int).T
                    return field[y,x]+rng.uniform(0,.003,count)
                angle=float(r.par.Sensor)
                left,right=sense(heading+angle),sense(heading-angle)
                heading+=np.where(np.maximum(left,right)>sense(heading),np.sign(left-right)*.38,0)
                nextpos=move(heading,.63)
                x,y=nextpos.astype(int).T
                valid=mask[y,x]
                positions[valid]=nextpos[valid]
                heading[~valid]+=rng.uniform(1.6,3.8,(~valid).sum())
                np.add.at(trail,(y[valid],x[valid]),float(r.par.Deposit))
                trail[:]=mask*np.minimum(1,(trail*(1-float(r.par.Diffusion))+cv2.blur(trail,(3,3))*float(r.par.Diffusion))*float(r.par.Retention))
    rgba=np.zeros((90,160,4),np.float32)
    rgba[:,:,:3]=trail[:,:,None]*np.array([.34,.18,.055])
    rgba[:,:,3]=1
    scriptOp.copyNumpyArray(rgba)
