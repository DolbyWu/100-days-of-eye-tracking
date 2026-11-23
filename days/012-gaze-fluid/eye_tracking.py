"""Conservative optical cues from Neon's 384x192 binocular eye video.

Centers and radii are video estimates. Millimeter pupil diameters come separately
from Neon eye-state data; no diagnosis or physiological inference is made here.
"""
import math


class EyeTracker:
    def __init__(self):
        import cv2
        import numpy as np
        self.cv2, self.np = cv2, np
        self.previous = None
        self.centers = [None, None]

    def update(self, bgr):
        cv2, np = self.cv2, self.np
        h,w = bgr.shape[:2]
        gray = cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
        small = cv2.GaussianBlur(gray,(0,0),max(2,w/64)).astype(np.float32)
        large = cv2.GaussianBlur(gray,(0,0),max(7,w/16)).astype(np.float32)
        score = large-small
        out={"eye_video_valid":1,"eye_video_w":w,"eye_video_h":h}
        for side in range(2):
            # The camera encodes two 192x192 views side by side. Restrict search
            # away from the eyelid and face edges, which can be darker than pupil.
            x0,x1 = ((.18,.42) if side==0 else (.57,.81))
            xa,xb=int(w*x0),int(w*x1)
            ya,yb=int(h*.13),int(h*.51)
            roi=score[ya:yb,xa:xb]
            _,peak,_,pos=cv2.minMaxLoc(roi)
            x,y=xa+pos[0],ya+pos[1]
            confidence=max(0.0,min(1.0,(peak-12)/32))
            key='eye_l' if side==0 else 'eye_r'
            if peak<18 or int(gray[y,x])>110:
                out.update({key+'_valid':0,key+'_x':0,key+'_y':0,key+'_radius':0,key+'_confidence':0})
                self.centers[side]=None
                continue
            previous=self.centers[side]
            if previous is not None:
                x=.55*previous[0]+.45*x
                y=.55*previous[1]+.45*y
            self.centers[side]=(x,y)
            ix,iy=int(round(x)),int(round(y))
            xlo,xhi=max(0,ix-30),min(w,ix+31)
            ylo,yhi=max(0,iy-30),min(h,iy+31)
            patch=score[ylo:yhi,xlo:xhi]
            radius=math.sqrt(float((patch>max(10,peak*.60)).sum())/math.pi)
            radius=max(8.0,min(30.0,radius))
            out.update({key+'_valid':1,key+'_x':x/w,key+'_y':y/h,
                        key+'_radius':radius/w,key+'_confidence':confidence})
        # Boxes mark frame-to-frame changes in the eye video, not neural events.
        changes=[]
        if self.previous is not None and self.previous.shape==gray.shape:
            delta=cv2.absdiff(gray,self.previous)
            delta=cv2.GaussianBlur(delta,(5,5),0)
            _,mask=cv2.threshold(delta,18,255,cv2.THRESH_BINARY)
            mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
            n,_,stats,_=cv2.connectedComponentsWithStats(mask)
            for i in range(1,n):
                x,y,bw,bh,area=map(int,stats[i])
                if 16<=area<=max(2000,w*h//8) and bw>=4 and bh>=4:
                    energy=float(delta[y:y+bh,x:x+bw].mean())
                    changes.append((energy*math.sqrt(area),x,y,bw,bh,energy))
        changes.sort(reverse=True)
        for i in range(3):
            prefix=f'eye_change{i}'
            if i<len(changes):
                _,x,y,bw,bh,energy=changes[i]
                out.update({prefix+'_valid':1,prefix+'_x':(x+bw/2)/w,
                            prefix+'_y':(y+bh/2)/h,prefix+'_w':bw/w,
                            prefix+'_h':bh/h,prefix+'_value':energy/255})
            else:
                out.update({prefix+'_valid':0,prefix+'_x':0,prefix+'_y':0,
                            prefix+'_w':0,prefix+'_h':0,prefix+'_value':0})
        self.previous=gray
        return out
