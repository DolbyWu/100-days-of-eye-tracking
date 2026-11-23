import json
from pathlib import Path
from queue import Queue, Full, Empty
import subprocess
from threading import Thread
from time import monotonic

import numpy as np

ASPECT = 16/9
RADIUS = .096
BONES = [(0,i) for i in (1,5,9,13,17)] + [(i,i+1) for i in range(1,20) if i%4 != 0]
BONES += [(5,9),(9,13),(13,17)]
_state = {}


class Hands:
    def __init__(self, helper):
        self.process = subprocess.Popen([str(helper), "640", "360"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.error = ""
        self.queue = Queue(maxsize=1)
        self.latest = (0, [])
        self.worker = Thread(target=self.run, daemon=True)
        self.worker.start()

    def run(self):
        try:
            while self.process.poll() is None:
                image = self.queue.get(timeout=8)
                if image is None:
                    break
                self.process.stdin.write(image)
                self.process.stdin.flush()
                line = self.process.stdout.readline()
                if not line:
                    return
                reply = json.loads(line)
                self.error = reply.get('error', '') if isinstance(reply, dict) else ''
                self.latest = monotonic(), reply if isinstance(reply, list) else []
        except Empty:
            pass
        except (OSError, ValueError) as exc:
            self.error = str(exc)
        finally:
            self.process.stdin.close()
            self.process.wait()
            self.process.stdout.close()

    def submit(self, image):
        try:
            self.queue.put_nowait(image)
        except Full:
            pass


def step(positions, velocities, dt, force, bones, fixed, skip_hand):
    for i, (p,v) in enumerate(zip(positions, velocities)):
        if fixed[i]:
            continue
        v += np.asarray(force)*dt
        v *= np.exp(-.55*dt)
        p += v*dt
        for axis, edge in enumerate((ASPECT,1)):
            if p[axis] < RADIUS or p[axis] > edge-RADIUS:
                p[axis] = np.clip(p[axis],RADIUS,edge-RADIUS)
                v[axis] = abs(v[axis])*.86 * (1 if p[axis] == RADIUS else -1)
        for a,b in (() if skip_hand[i] else bones):
            ab=b-a
            q=a+ab*np.clip(np.dot(p-a,ab)/max(np.dot(ab,ab),1e-8),0,1)
            delta=p-q
            distance=np.linalg.norm(delta)
            if distance < RADIUS+.017:
                normal=delta/max(distance,1e-6) if distance > 1e-6 else np.array([0.,1.])
                p[:]=q+normal*(RADIUS+.018)
                inward=np.dot(v,normal)
                v += normal*(.24-1.75*min(0,inward))
        p[:]=np.clip(p,[RADIUS,RADIUS],[ASPECT-RADIUS,1-RADIUS])
    delta=positions[1]-positions[0]
    distance=np.linalg.norm(delta)
    if 1e-6 < distance < 2*RADIUS and not all(fixed):
        normal=delta/distance
        share=(~fixed).astype(float) / np.count_nonzero(~fixed)
        correction=normal*(2*RADIUS-distance)
        positions[0]-=share[0]*correction
        positions[1]+=share[1]*correction
        speed=np.dot(velocities[1]-velocities[0],normal)
        if speed < 0:
            velocities[0]+=share[0]*1.86*speed*normal
            velocities[1]-=share[1]*1.86*speed*normal
    speed=np.linalg.norm(velocities,axis=1)
    velocities[~fixed] *= np.minimum(1,1.5/np.maximum(speed[~fixed],1e-6))[:,None]


# Vision reports normalized joints in bottom-left coordinates. Use display-height
# units for BOTH axes so pinch distances are independent of the window aspect.
def display_hand(observation, mirror):
    points = np.asarray(observation, dtype=float).copy()
    if mirror:
        points[:, 0] = 1 - points[:, 0]
    points[:, 0] *= ASPECT
    return points


class Pinches:
    def __init__(self):
        self.tracks = []
        self.until = np.zeros(2)       # short stop on release
        self.clear_hand = np.zeros(2)  # let opening fingers leave the disc
        self.stamp = None

    def release(self, track, now, velocities):
        eye = track.get('eye')
        if eye is not None:
            velocities[eye] = 0
            self.until[eye] = now + .20
            self.clear_hand[eye] = now + .48
        track.update(eye=None, closed=False)

    def update(self, hands, stamp, now, positions, velocities):
        for track in self.tracks:
            if now - track['tips_seen'] > .20 and track['closed']:
                self.release(track, now, velocities)
        self.tracks = [t for t in self.tracks if now - t['seen'] < .32]
        if stamp == self.stamp or now - stamp > .25:
            return
        self.stamp = stamp
        palms = []
        for hand in hands:
            base = hand[[0, 5, 9, 13, 17]]
            visible = base[base[:, 2] >= .25, :2]
            if len(visible) >= 2:
                palms.append((hand, visible.mean(axis=0)))
        # Vision can reorder left and right on successive frames.
        candidates = sorted((np.linalg.norm(t['anchor']-p), i, j)
                            for i, t in enumerate(self.tracks)
                            for j, (_, p) in enumerate(palms))
        matched, used = {}, set()
        for distance, i, j in candidates:
            if distance < .32 and i not in used and j not in matched:
                matched[j] = self.tracks[i]
                used.add(i)
        for j, (hand, anchor) in enumerate(palms):
            track = matched.get(j)
            if track is None:
                track = dict(closed=False, eye=None, tips_seen=0.)
                self.tracks.append(track)
            track.update(seen=now, anchor=anchor)
            if min(hand[4, 2], hand[8, 2]) < .25:
                continue
            # Scale thresholds by palm dimensions for near and far hands.
            spans = [np.linalg.norm(hand[a,:2]-hand[b,:2]) for a,b in ((0,9),(5,17))
                     if min(hand[a,2],hand[b,2]) >= .25]
            if not spans:
                continue
            span = max(.035, max(spans))
            tips = hand[[4,8], :2]
            gap = np.linalg.norm(tips[1] - tips[0]) / span
            center = tips.mean(axis=0)
            track['tips_seen'] = now
            if track['closed']:
                if gap > .55:
                    self.release(track, now, velocities)
                elif track['eye'] is not None:
                    track['target'] = center + track['offset']
            elif gap < .34:
                track['closed'] = True
                taken = {t['eye'] for t in self.tracks if t['eye'] is not None}
                choices = [(np.linalg.norm(p-center), i) for i, p in enumerate(positions) if i not in taken]
                if choices:
                    distance, eye = min(choices)
                    if distance <= RADIUS + .055:
                        track.update(eye=eye, target=positions[eye].copy(),
                                     offset=positions[eye]-center)
                        velocities[eye] = 0

    def targets(self):
        return {t['eye']: t['target'] for t in self.tracks if t['eye'] is not None}


def advance(positions, velocities, strain, strain_velocity, dt, force, bones, pinches, now):
    targets = pinches.targets()
    for _ in range(3):
        h = dt / 3
        fixed = np.array([i in targets or now < pinches.until[i] for i in range(2)])
        # Only unheld eyes should bounce off bones or be pushed by another disc.
        step(positions, velocities, h, force, bones, fixed, now < pinches.clear_hand)
        for i in range(2):
            desired = np.zeros(2)
            if i in targets:
                target = np.clip(targets[i], [RADIUS,RADIUS], [ASPECT-RADIUS,1-RADIUS])
                error = target - positions[i]
                velocities[i] += (310*error - 27*velocities[i])*h
                positions[i] += velocities[i]*h
                positions[i] = np.clip(positions[i], [RADIUS,RADIUS], [ASPECT-RADIUS,1-RADIUS])
                speed = np.linalg.norm(velocities[i])
                if speed > .015:
                    x, y = velocities[i] / speed
                    desired = min(.125, speed*.13) * np.array([x*x-y*y, 2*x*y])
                desired[0] -= .025
            # An underdamped shape spring gives a small wobble even after the
            # centre stops. The two components describe stretch, never rotation.
            strain_velocity[i] += (230*(desired-strain[i])-13*strain_velocity[i])*h
            strain[i] += strain_velocity[i]*h


def onCook(scriptOp):
    _=absTime.frame
    root=scriptOp.parent()
    now=monotonic()
    if not _state:
        _state.update(positions=np.array([[.60,.55],[1.16,.59]]),
                      velocities=np.array([[.20,.12],[-.18,-.10]]),
                      last=now, scan=0, pinches=Pinches(), strain=np.zeros((2,2)),
                      strain_velocity=np.zeros((2,2)),
                      clock=None, heartbeat=-100)
    s=_state
    osc=root.op('neon_osc')
    def channel(name, default=0):
        chans=osc.chans(name) or osc.chans('/'+name)
        return float(chans[0][osc.numSamples-1]) if chans and osc.numSamples else default
    clock=channel('clock',-1)
    if clock>=0 and clock!=s['clock']:
        s.update(clock=clock, heartbeat=now)
    fresh=now-s['heartbeat']<.35
    if now>s.get('url_poll',0):
        length=int(channel('eye_url_n'))
        if fresh and 0<length<=240:
            try:
                url=b''.join(int(channel('eye_url'+str(i))).to_bytes(3,'big')
                             for i in range((length+2)//3))[:length].decode()
                if url.startswith('rtsp://') and not root.par.Manualeye.eval():
                    root.par.Liveeye=url
            except (ValueError,OverflowError):
                pass
        s['url_poll']=now+.6
    camera=root.op('hand_frame')
    hands=[]
    bones=[]
    stamp=0
    status='off'
    if root.par.Hands.eval() and root.par.Webcam.eval() and not root.par.Demo.eval():
        tracker=s.get('hands')
        if tracker is None or not tracker.worker.is_alive():
            if now >= s.get('retry', 0):
                s['retry']=now+1
                try:
                    tracker=s['hands']=Hands(Path(project.folder)/'day13-hands')
                except OSError as exc:
                    s['hand_error']=str(exc)
        if tracker is not None and tracker.worker.is_alive():
            status='waiting for camera'
            if now-s['scan'] >= 1/24:
                frame=camera.numpyArray(delayed=True)
                if frame is not None and frame.shape == (360,640,4):
                    tracker.submit(np.asarray(np.clip(frame[::-1]*255,0,255),dtype=np.uint8).tobytes())
                elif frame is not None:
                    status=f'unexpected frame {frame.shape}'
                s['scan']=now
            stamp, observations=tracker.latest
            if now-stamp < .25:
                hands=[display_hand(h, root.par.Mirror.eval()) for h in observations]
                status=tracker.error or f'{len(hands)} hands'
                for hand in hands:
                    bones.extend((hand[i,:2],hand[j,:2]) for i,j in BONES
                                 if min(hand[i,2],hand[j,2]) > .25)
        else:
            status=s.get('hand_error','restarting tracker')
    s['hand_status']=status
    pinches=s['pinches']
    pinches.update(hands, stamp, now, s['positions'], s['velocities'])
    dt=min(.055,max(.001,now-s['last']))
    s['last']=now
    demo=root.par.Demo.eval()
    direction=np.array([0.,0.])
    if demo:
        direction=np.array([np.sin(now*.9),np.cos(now*1.3)])*.6
        wrist=np.array([.89+.27*np.sin(now*.6),.39])
        tips=[wrist+np.array([(i-2)*.06,.29-abs(i-2)*.035]) for i in range(5)]
        bones=[(wrist,tip) for tip in tips]
    elif fresh and channel('valid'):
        if channel('eye_l_valid') and channel('eye_r_valid'):
            gaze=np.array([(channel('eye_l_x')+channel('eye_r_x')-.99)*4,
                           ( .68-channel('eye_l_y')-channel('eye_r_y'))*2.3])
        else:
            gaze=np.array([(channel('gx',.5)-.5)*2,(channel('gy',.5)-.5)*2])
        direction=np.clip(gaze,-1,1)
    direction[np.abs(direction)<.085]=0
    if root.par.Mirror.eval() and not demo:
        direction[0]*=-1
    advance(s['positions'],s['velocities'],s['strain'],s['strain_velocity'],dt,
            direction*1.18,bones,pinches,now)
    payload=np.zeros((1,49,4),dtype=np.float32)
    payload[0,:2,:2]=s['positions']
    payload[0,:2,2:]=s['strain']
    payload[0,2]=min(len(bones),46),bool(demo),bool(root.par.Mirror.eval()),bool(root.par.Webcam.eval() and not demo)
    for i,(a,b) in enumerate(bones[:46]):
        payload[0,i+3]=*a,*b
    scriptOp.copyNumpyArray(payload)
