"""Book figure detection and the silk-to-print transition (top-left pixel space)."""
import math

import cv2
import numpy as np


def local_figures(image, words):
    # Cluster non-text edges on the framed page. Keeping the processing scale
    # fixed makes stroke gaps and minimum figure size camera-independent.
    h,w=image.shape[:2]
    small=cv2.resize(image,(768,max(1,round(768*h/w))))
    h,w=small.shape[:2]
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,45,125)
    for word in words:
        a,b,c,d=np.rint(np.asarray(word['box'])*[w,h,w,h]).astype(int)
        cv2.rectangle(edges,(a-2,b-2),(c+2,d+2),0,-1)
    connected=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((13,15),np.uint8))
    connected=cv2.dilate(connected,np.ones((5,5),np.uint8))
    _,labels,stats,_=cv2.connectedComponentsWithStats(connected)
    result=[]
    for label,(x,y,bw,bh,_) in enumerate(stats[1:],start=1):
        area=bw*bh/(w*h)
        if not .009<area<.94 or min(bw,bh)<28: continue
        patch=edges[y:y+bh,x:x+bw]*(labels[y:y+bh,x:x+bw]==label)
        if np.count_nonzero(patch)<.016*bw*bh: continue
        # Reject outlines of a blank page, monitor or picture frame.
        if not np.any(patch[bh//6:-bh//6,bw//6:-bw//6]): continue
        result.append({'kind':'figure','box':[x/w,y/h,(x+bw)/w,(y+bh)/h]})
    return sorted(result,key=lambda f:tuple(f['box'][1::-1]))


def demo_figure():
    h,w=420,720
    page=np.full((h,w,3),247,np.uint8)
    box=[.32,.76,.69,.96]
    x,y,r,b=np.rint(np.array(box)*[w,h,w,h]).astype(int)
    patch=page[y:b,x:r]
    patch[:]=(59,47,29)
    u=np.linspace(0,1,r-x)
    for i in range(6):
        v=.5+.27*np.sin(7*u+i*.42)*np.sin(np.pi*u)+.045*(i-3)
        pts=np.int32(np.c_[u*(r-x-1),v*(b-y-1)])
        cv2.polylines(patch,[pts],False,(156+i*9,210-i*7,100+i*20),1,cv2.LINE_AA)
    return page,[{'kind':'chart','box':box}]


def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*(3-2*t)


class SilkFigure:
    def __init__(self,source,kind,box,home,size):
        self.kind,self.box,self.home=kind,np.asarray(box),np.asarray(home)
        h,w=source.shape[:2]
        l,t=np.floor(self.box[:2]*[w,h]).astype(int)
        r,b=np.ceil(self.box[2:]*[w,h]).astype(int)
        rgb=cv2.cvtColor(source[t:b,l:r],cv2.COLOR_BGR2RGB)
        # Fit the actual camera pixels into the same page layout as the type.
        scale=min(size[0]/rgb.shape[1],size[1]/rgb.shape[0])
        self.rgb=cv2.resize(rgb,(max(2,round(rgb.shape[1]*scale)),max(2,round(rgb.shape[0]*scale))),interpolation=cv2.INTER_AREA)
        self.birth=None

    def release(self,eye,now):
        self.origin=eye[:2].copy()
        self.direction=1 if eye[0]<640 else -1
        self.birth=now

    def paint(self,layer,now):
        if self.birth is None: return
        age=max(0.,now-self.birth)
        H,W=layer.shape[:2]
        h,w=self.rgb.shape[:2]
        start=self.origin
        # Unfurl sideways first, then let the fully formed print drop.
        crest=np.clip(start+[self.direction*(135+w*.30),-75],[w/2,h/2],[W-w/2,H-h/2])
        land=np.array([crest[0],min(H-h/2-5,crest[1]+190)])
        if age<1.35:
            t=age/1.35
            center=start+(crest-start)*smooth(t)
            width=max(3,round(w*(.07+.93*smooth(t))))
            height=max(3,round(h*(.10+.90*smooth(t))))
            amplitude=(1-smooth(t))*min(34,h*.30)
            pad=math.ceil(amplitude*1.45)+2
            u=np.linspace(0,1,width,dtype=np.float32)[None,:]
            y=np.arange(height+2*pad,dtype=np.float32)[:,None]
            phase=2*math.pi*(1.35*u*self.direction-1.65*t)
            fold=(1-smooth(t))*(.16+.15*np.sin(phase))
            mid=height/2+pad+amplitude*np.sin(phase)*(.48+.52*u)
            v=(y-mid)/(height*(1-fold))+.5
            mapx=np.broadcast_to(u*(w-1),v.shape).copy()
            rgb=cv2.remap(self.rgb,mapx,np.float32(v*(h-1)),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
            # Parallel bands drift over the printed texture like layers of gauze.
            ripple=.5+.5*np.cos(23*v+phase)
            gauze=(.20+.44*ripple)*np.clip(np.minimum(v,1-v)*13,0,1)
            opacity=(1-smooth(t))*gauze+smooth(t)
            a=np.uint8(255*np.clip(opacity,0,1)*((v>=0)&(v<=1)))
        else:
            if age<2.1:
                center=crest+(land-crest)*((age-1.35)/.75)**2
            else:
                center=land+(self.home-land)*smooth((age-2.1)/1.25)
            rgb=self.rgb
            a=None
        hh,ww=rgb.shape[:2]
        x=int(round(center[0]-ww/2)); y=int(round(center[1]-hh/2))
        l,t=max(0,x),max(0,y); r,b=min(W,x+ww),min(H,y+hh)
        if r<=l or b<=t:return
        dst=layer[t:b,l:r]
        rgb=rgb[t-y:b-y,l-x:r-x]
        if a is None:
            dst[:,:,:3]=rgb
            dst[:,:,3]=255
        else:
            alpha=a[t-y:b-y,l-x:r-x,None].astype(np.float32)/255
            dst[:,:,:3]=rgb*alpha+dst[:,:,:3]*(1-alpha)
            dst[:,:,3:]=255*alpha+dst[:,:,3:]*(1-alpha)
