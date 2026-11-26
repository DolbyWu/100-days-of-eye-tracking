"""Timestamped combined-gaze adapter and illustrative region envelopes."""
import math

def demo(t):
    phase=t%5
    x=.26 if phase<1.6 else min(.76,.26+(phase-1.6)*4)
    if phase>2.5:
        x=.76-.49*(phase-2.5)/2.5
    return dict(session=0,gaze_t=t,valid=int(phase<4.8),gx=x,gy=.5+.02*math.sin(t),
                pupil_l=3.7+.35*math.sin(t),pupil_r=3.8+.35*math.sin(t),blink=int(t/5))

class Signals:
    def __init__(self,config):
        self.cfg=config
        self.session=None
        self.level={}
        self.reset()

    def reset(self):
        self.sample=None
        self.last_seen=-math.inf
        self.still=0
        self.moving=0
        self.event=''
        self.count=None
        self.flash_until=-math.inf
        self.baseline=None
        self.pupil=0
        self.direction=(0,0)
        self.last_frame=None
        self.level.clear()

    def step(self,p,now,manual=''):
        if self.session!=p.get('session'):
            self.reset()
            self.session=p.get('session')
        dt=0 if self.last_frame is None else max(0,now-self.last_frame)
        self.last_frame=now
        th=self.cfg['thresholds']
        stamp=p.get('gaze_t')
        count=p.get('blink')
        if count is not None and self.count is not None and count>self.count:
            self.flash_until=now+.16
        self.count=count
        good=p.get('valid')==1 and stamp is not None and math.isfinite(stamp) and all(
            v is not None and math.isfinite(v) and 0<=v<=1 for v in (p.get('gx'),p.get('gy')))
        if not good:
            self.sample=None
            self.event=''
            self.still=self.moving=self.pupil=0
        elif self.sample is None or stamp>self.sample[0]:
            x,y=p['gx'],p['gy']
            gap=stamp-self.sample[0] if self.sample else 0
            if 0<gap<th['stale_s']:
                speed=math.hypot(x-self.sample[1],y-self.sample[2])/gap
                threshold=th['saccade_off_uv_s'] if self.event=='saccade' else th['saccade_on_uv_s']
                self.still=self.still+gap if speed<th['still_uv_s'] else 0
                self.moving=self.moving+gap if th['still_uv_s']<=speed<threshold else 0
                self.event=('saccade' if speed>=threshold else 'fixation' if self.still>=th['fixation_s']
                            else 'smooth_motion' if self.moving>=.12 else '')
            else:
                self.still=self.moving=0
                self.event=''
            self.direction=(2*x-1,2*y-1)
            self.sample=(stamp,x,y)
            self.last_seen=now
            diam=[v for v in (p.get('pupil_l'),p.get('pupil_r')) if v is not None and 0<v<12]
            self.pupil=0
            if diam and now>self.flash_until:
                mean=sum(diam)/len(diam)
                if self.baseline is None: self.baseline=mean
                self.baseline+=(mean-self.baseline)*(-math.expm1(-min(gap,.4)/8))
                self.pupil=max(0,min(1,mean-self.baseline))
        stale=now-self.last_seen>=th['stale_s'] or not good
        if stale:
            self.event=''
            self.still=self.moving=self.pupil=0
            self.direction=(0,0)
        event=manual or ('blink' if now<self.flash_until else self.event)
        targets=self.cfg.get(event,{})
        for region in set(self.level)|set(targets):
            old=self.level.get(region,0)
            target=targets.get(region,0)
            tau=(.03 if event=='saccade' else .18) if target>old else .55
            self.level[region]=old+(target-old)*(-math.expm1(-dt/tau))
        return self.level
