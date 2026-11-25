import json
from pathlib import Path
from queue import Queue, Full, Empty
import subprocess
from threading import Thread
from time import monotonic

import numpy as np

ASPECT = 16/9
RADIUS = .096
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


def display_hand(observation, mirror):
    points = np.asarray(observation, dtype=float).copy()
    if mirror:
        points[:, 0] = 1 - points[:, 0]
    points[:, 0] *= ASPECT
    return points


class EyeHandles:
    def __init__(self):
        self.positions=np.array([[.57,.73],[1.20,.73]])
        self.radii=np.array([.11,.11])
        self.tracks=[]
        self.stamp=None
        self.serial=0
        self.bindings=[None,None]

    def update(self,hands,stamp,now):
        self.tracks=[t for t in self.tracks if now-t['seen']<.23]
        for track in self.tracks:
            if now-track['tips_seen']>.19: track.update(eye=None,closed=False)
        if self.stamp!=stamp and now-stamp<.25:
            self.observe(hands,now)
        self.stamp=stamp
        for eye in range(2):
            grips=sorted((t['id'],t['center']) for t in self.tracks if t['eye']==eye)
            if not grips:
                self.bindings[eye]=None
                continue
            ids=tuple(g[0] for g in grips)
            midpoint=np.mean([g[1] for g in grips],axis=0)
            span=np.linalg.norm(grips[-1][1]-grips[0][1])
            binding=self.bindings[eye]
            if binding is None or binding[0]!=ids:
                binding=self.bindings[eye]=(ids,midpoint,self.positions[eye].copy(),max(.025,span),self.radii[eye])
            if len(ids)==2:
                self.radii[eye]=np.clip(binding[4]*span/binding[3],.035,.36)
            r=self.radii[eye]
            self.positions[eye]=np.clip(binding[2]+midpoint-binding[1],[r,r],[ASPECT-r,1-r])

    def observe(self,hands,now):
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
                self.serial+=1
                track = dict(id=self.serial,closed=False,eye=None,tips_seen=0.)
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
            track.update(tips_seen=now,center=center)
            if track['closed']:
                if gap>.55: track.update(closed=False,eye=None)
            elif gap<.34:
                track['closed']=True
                distances=np.linalg.norm(self.positions-center,axis=1)
                choices=[i for i in range(2) if distances[i]<=self.radii[i]+.045
                         and sum(t['eye']==i for t in self.tracks)<2]
                if choices: track['eye']=min(choices,key=lambda i:distances[i]/self.radii[i])
