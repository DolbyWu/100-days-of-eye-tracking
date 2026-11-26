"""Batched instance positions on schematic crossed/uncrossed centerlines."""
import json
import numpy as np
routes=None

def onCook(scriptOp):
    global routes
    t=absTime.seconds
    root=scriptOp.parent()
    if routes is None:
        meta=json.loads(root.op('landmarks').text)
        routes=[]
        for side,other in [('L','R'),('R','L')]:
            for dest in (side,other):
                names=['eye_'+side,'chiasm','tract_'+dest,'LGN_'+dest,'V1_'+dest]
                pts=np.array([meta[n] for n in names])
                # Push the schematic optic radiation laterally around the ventricle.
                bend=(pts[-2]+pts[-1])*.5
                bend[0]+=.19 if dest=='L' else -.19
                pts=np.insert(pts,4,bend,axis=0)
                routes.append(pts)
    count=int(root.par.Particles)
    feature=root.op('features')
    flow=float(feature['flow'])
    phase=np.arange(count)/count
    positions=[]
    for i,pts in enumerate(routes):
        u=(phase+t*(.13+.12*flow)*(1-.68*int(root.par.Reduced))+.13*i)%1
        k=u*(len(pts)-1)
        seg=k.astype(int)
        f=(k-seg)[:,None]
        positions.append(pts[seg]*(1-f)+pts[seg+1]*f)
    xyz=np.concatenate(positions)
    scriptOp.clear()
    scriptOp.numSamples=len(xyz)
    for i,name in enumerate('xyz'):
        scriptOp.appendChan(name).vals=xyz[:,i].tolist()
