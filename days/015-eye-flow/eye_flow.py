import cv2
import numpy as np
from time import monotonic

previous = None
points = np.empty((0, 2), np.float32)
ids = ages = np.empty(0, int)
speeds = np.empty(0)
serial = 0
stamp = 0

def pupil_box(eye):
    """Find a compact dark pupil surrounded by a brighter iris."""
    h, w = eye.shape
    smooth = cv2.medianBlur(eye, 5)
    best = None
    score = 0
    for threshold in range(8, 65, 4):
        contours, _ = cv2.findContours(np.uint8(smooth <= threshold), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, a, b = cv2.boundingRect(contour)
            if not (7 <= a <= w*.32 and 7 <= b <= h*.32 and .42 < a/b < 1.65):
                continue
            if min(x,y,w-x-a,h-y-b)<4 or len(contour)<5:
                continue
            fill = cv2.contourArea(contour)/(a*b)
            if not .58 < fill < .9:
                continue
            patch = smooth[y-4:y+b+4,x-4:x+a+4]
            border = np.concatenate((patch[0],patch[-1],patch[:,0],patch[:,-1]))
            core = smooth[y+b//4:y+3*b//4+1,x+a//4:x+3*a//4+1]
            contrast = np.median(border)-float(np.median(core))
            quality = contrast * fill * min(1,a*b/180)
            if contrast>=10 and quality>score:
                best,score=(x,y,a,b),quality
    return best

def onCook(scriptOp):
    global previous, points, ids, ages, speeds, serial, stamp
    _ = absTime.frame
    raw = scriptOp.inputs[0].numpyArray(delayed=False)
    if raw is None:
        return
    gray = np.ascontiguousarray((raw[::-1,:,0].clip(0,1)*255).astype('uint8'))
    h,w = gray.shape
    now = monotonic()
    changed = previous is None or previous.shape != gray.shape or not np.array_equal(gray, previous)
    if changed:
        if previous is None or previous.shape != gray.shape or now-stamp > .6:
            points,ids,ages,speeds = points[:0],ids[:0],ages[:0],speeds[:0]
        if len(points):
            p, ok, err = cv2.calcOpticalFlowPyrLK(previous,gray,points,None,winSize=(13,13),maxLevel=2)
            back, ok2, _ = cv2.calcOpticalFlowPyrLK(gray,previous,p,None,winSize=(13,13),maxLevel=2)
            keep = (ok.ravel()>0)&(ok2.ravel()>0)&(err.ravel()<25)&(np.linalg.norm(back-points,axis=1)<1.3)&(p[:,0]>=0)&(p[:,0]<w)&(p[:,1]>=0)&(p[:,1]<h)&((p[:,0]<w/2)==(points[:,0]<w/2))
            speed = np.linalg.norm(p-points,axis=1)/max(.001,now-stamp)
            points,ids,ages,speeds = p[keep],ids[keep],ages[keep]+1,(.7*speeds+.3*speed)[keep]
        if len(points)<145:
            mask=np.full_like(gray,255)
            mask[:,w//2-3:w//2+3]=0
            for x,y in points.astype(int):
                cv2.circle(mask,(x,y),5,0,-1)
            new=cv2.goodFeaturesToTrack(gray,180-len(points),.009,5,mask=mask,blockSize=3)
            if new is not None:
                n=len(new)
                points=np.vstack((points,new.reshape(-1,2)))
                ids=np.r_[ids,np.arange(serial,serial+n)]
                ages=np.r_[ages,np.zeros(n,int)]
                speeds=np.r_[speeds,np.zeros(n)]
                serial+=n
        previous,stamp=gray,now
    width=960
    scale=width/w
    canvas=cv2.cvtColor(cv2.resize(gray,(width,round(h*scale))),cv2.COLOR_GRAY2RGB)
    boxes=[]
    for start in (0,w//2):
        box=pupil_box(gray[:,start:start+w//2])
        if box:
            x,y,a,b=box
            boxes.append((x+start,y,a,b))
    colors=((201,226,52),(168,184,64),(222,250,72))
    if 'blink_colors' in globals():
        colors=blink_colors(parent())
    groups={}
    for i,(x,y) in enumerate(points):
        px,py=round(x*scale),round(y*scale)
        near=any(((x-bx-bw/2)/(bw*2))**2+((y-by-bh/2)/(bh*1.6))**2<1 for bx,by,bw,bh in boxes)
        if boxes and not near and ids[i]%5:continue
        radius=3+min(4,int(speeds[i]/35))
        cv2.rectangle(canvas,(px-radius,py-radius),(px+radius,py+radius),colors[0],1,cv2.LINE_AA)
        groups.setdefault((int(x>=w/2),int(x//35),int(y//29)),[]).append(i)
    group_bounds=[]
    labels=[]
    for members in sorted(groups.values(),key=len,reverse=True):
        if len(members)<4:continue
        corners=points[members]*scale
        anchor=max(range(len(members)),key=lambda j:ages[members[j]])
        distances=np.linalg.norm(corners-corners[anchor],axis=1)
        for j in np.argsort(distances)[1:3]:
            if distances[j]>10:
                cv2.line(canvas,tuple(corners[anchor].astype(int)),tuple(corners[j].astype(int)),colors[1],1,cv2.LINE_AA)
        lo=(corners.min(0)-6).astype(int)
        hi=(corners.max(0)+6).astype(int)
        group_bounds.append((lo,hi))
        cv2.rectangle(canvas,lo,hi,colors[1],1,cv2.LINE_AA)
        i=max(members,key=lambda j:ages[j])
        if ages[i]>=8 and len(labels)<4 and all(np.linalg.norm(lo-q)>100 for q in labels):
            cv2.putText(canvas,f'#{ids[i]:04}  {speeds[i]:.0f} px/s',(max(2,min(width-112,lo[0])),max(13,lo[1]-4)),cv2.FONT_HERSHEY_SIMPLEX,.34,(255,255,255),1,cv2.LINE_AA)
            labels.append(lo)
    pupil_rects=[tuple(round(v*scale) for v in box) for box in boxes]
    for index,(lo,hi) in enumerate(group_bounds):
        center=(lo+hi)/2
        candidates=sorted(group_bounds[:index],key=lambda pair: np.linalg.norm((pair[0]+pair[1])/2-center))
        for other_lo,other_hi in candidates:
            delta=(other_lo+other_hi)/2-center
            if np.linalg.norm(delta)>width*.42:
                break
            unit=np.maximum(np.abs(delta),.001)
            start=center+delta*np.min((hi-lo)/(2*unit))
            end=center+delta-delta*np.min((other_hi-other_lo)/(2*unit))
            if np.dot(end-start,delta)<=0:
                continue
            start,end=tuple(start.astype(int)),tuple(end.astype(int))
            if any(cv2.clipLine(rect,start,end)[0] for rect in pupil_rects):
                continue
            cv2.line(canvas,start,end,colors[1],1,cv2.LINE_AA)
            break
    scriptOp.store('fire_visible_at',now if boxes and globals().get('pupil_fire') else -1)
    for x,y,a,b in boxes:
        if "pupil_detail" in globals():
            pupil_detail(canvas,(x,y,a,b),scale,parent(),now)
        cv2.rectangle(canvas,(round(x*scale)-2,round(y*scale)-2),(round((x+a)*scale)+2,round((y+b)*scale)+2),colors[2],1,cv2.LINE_AA)
    if gray.max()<3:
        cv2.putText(canvas,'Waiting for Neon eye video',(24,48),cv2.FONT_HERSHEY_SIMPLEX,.7,(240,240,240),1,cv2.LINE_AA)
    scriptOp.copyNumpyArray(np.ascontiguousarray(cv2.cvtColor(canvas,cv2.COLOR_RGB2RGBA)[::-1]))
