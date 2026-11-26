from time import monotonic
import cv2
import numpy as np
rng=np.random.default_rng(17)
dust=np.empty((0,8))
last=0.
def onCook(scriptOp):
    global dust,last
    _=absTime.frame
    parent=scriptOp.parent()
    hands=parent.op('hand_input')
    hands.cook()
    now=monotonic()
    dt=min(.1,now-last)
    last=now
    speed=hands.fetch('speed',0)
    w=int(parent.par.Width)
    h=round(w*9/16)
    img=np.zeros((h,w,4),np.uint8)
    if abs(speed)>3:
        frame=scriptOp.inputs[0].numpyArray(delayed=True)
        if frame is not None:
            rgb=frame[:,:,:3]
            yy,xx=np.where(rgb.max(2)>.095)
            if len(xx):
                pick=rng.choice(len(xx),min(110,int(abs(speed)*dt*9)+1))
                x=(xx[pick]+.5)*w/frame.shape[1]
                y=(yy[pick]+.5)*h/frame.shape[0]
                color=rgb[yy[pick],xx[pick]]*255
                turn=np.clip(-np.radians(speed)*.22,-2,2)
                depth=np.sqrt(np.clip(1-((x-w/2)/(.24*w))**2,0,1))
                vel=np.column_stack((turn*(18+42*depth),np.zeros(len(x))))+rng.normal(0,3,(len(x),2))
                dust=np.vstack((dust,np.column_stack((x,y,vel,color,rng.uniform(.28,.75,len(x))))))
    dust[:,7]-=dt
    dust=dust[dust[:,7]>0][-1800:]
    dust[:,:2]+=dust[:,2:4]*dt
    ix,iy=dust[:,:2].astype(int).T
    ok=(ix>=0)&(ix<w)&(iy>=0)&(iy<h)
    img[iy[ok],ix[ok],:3]=np.clip(dust[ok,4:7]*1.4,0,255)
    img[iy[ok],ix[ok],3]=np.clip(dust[ok,7]*420,0,230)
    img=np.ascontiguousarray(img[::-1])
    for label,pts in hands.fetch('lines',[]):
        a,b=[(int(x*w),int((1-y)*h)) for x,y in pts]
        cv2.line(img,a,b,(178,237,242,230),1,cv2.LINE_AA)
        for p in (a,b):cv2.circle(img,p,3,(230,251,252,245),1,cv2.LINE_AA)
        anchor=(int(np.clip((a[0]+b[0])/2-17,4,w-48)),int(np.clip((a[1]+b[1])/2-5,15,h-4)))
        cv2.putText(img,label,anchor,cv2.FONT_HERSHEY_SIMPLEX,.34*w/960,(250,251,245,255),1,cv2.LINE_AA)
    draw_dashboard(img,parent,now)
    scriptOp.copyNumpyArray(np.ascontiguousarray(img[::-1]))
