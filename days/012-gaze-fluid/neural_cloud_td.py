"""Render the Blender PLY and its live telemetry into a TouchDesigner Script TOP."""
import math
from pathlib import Path
from time import monotonic

import numpy as np

CELLS = np.array([[.219,.665],[.61,.76],[.843,.30],[.342,.139]], dtype=np.float32)
ASPECT = 1290 / 876
WIDTH, HEIGHT = 1200, 815
BLINK_WINDOW = 1.6
CLOSED_SECONDS = 3.0
REGROUP_SECONDS = 1.05
_clouds = {}
GLYPHS = {
    "0":"69996","1":"26227","2":"6912f","3":"e161e","4":"99f11",
    "5":"f8e1e","6":"68e96","7":"f1244","8":"69696","9":"69716",
    "A":"69f99","B":"e9e9e","C":"78887","D":"e999e","E":"f8e8f",
    "F":"f8e88","G":"78b97","H":"99f99","I":"72227","J":"11196",
    "K":"9aca9","L":"8888f","M":"9ff99","N":"9ddb9",
    "O":"69996","P":"e9e88","R":"e9ea9","S":"7861e","T":"f4444",
    "U":"99996","V":"99966","W":"99ff9","X":"99699","Y":"99644","Z":"f124f",
    ".":"00002",":":"02020","-":"00f00","+":"04e40","=":"0e0e0",
    "%":"92489","/":"12248","*":"0a4a0","(":"24842",")":"84248",
}


def read_cloud(path):
    with Path(path).open("rb") as ply:
        head = [ply.readline().strip() for _ in range(10)]
        if head[:2] != [b"ply", b"format ascii 1.0"] or head[-1] != b"end_header":
            raise ValueError("Expected the Day 12 ASCII XYZ/RGB PLY")
        points = np.loadtxt(ply, dtype=np.float32, ndmin=2)
    if points.shape != (int(head[2].split()[-1]), 6) or not np.isfinite(points).all():
        raise ValueError("Invalid point count or coordinates")
    return points


def update_gesture(state, now, fresh, worn, blink, apertures):
    """Use the blink counter for the burst and both measured lids for the reset."""
    if fresh and blink > state["blink"]:
        state["pulse"] = now
        if worn and state.get("burst") is None:
            recent = [stamp for stamp in state.get("blink_times", ())
                      if now-stamp <= BLINK_WINDOW]
            recent.append(now)
            if len(recent) == 3:
                state["burst"] = now
                recent.clear()
            state["blink_times"] = recent
    state["blink"] = blink
    if not fresh or not worn:
        state["blink_times"] = []
    if state.get("burst") is None:
        return 0., 0.

    if state.get("regroup") is not None:
        fraction = min(1., max(0., (now-state["regroup"])/REGROUP_SECONDS))
        if fraction == 1.:
            state.update(burst=None, regroup=None, closed_at=None)
        return 1.-fraction*fraction*(3.-2.*fraction), CLOSED_SECONDS

    closed = fresh and worn and all(0 <= value <= 2.0 for value in apertures)
    if closed:
        if state.get("closed_at") is None:
            state["closed_at"] = now
    else:
        state["closed_at"] = None
    elapsed = now-state["closed_at"] if state["closed_at"] is not None else 0.
    if elapsed >= CLOSED_SECONDS:
        state["regroup"] = now
        return 1., CLOSED_SECONDS
    phase = min(1., max(0., (now-state["burst"])/.85))
    return 1.-(1.-phase)**3, elapsed


def eye_stream_url(channel, fresh):
    count = int(channel("eye_url_n"))
    if not fresh or not 0 < count <= 240:
        return ""
    try:
        payload = b"".join(int(channel(f"eye_url{i}")).to_bytes(3,"big")
                           for i in range((count+2)//3))
        url = payload[:count].decode("utf-8")
    except (ValueError, OverflowError):
        return ""
    return url if url.startswith("rtsp://") else ""


class Cloud:
    def __init__(self, points):
        self.xyz = points[:, :3].copy()
        self.rgb = points[:, 3:] / 255
        self.uv = self.xyz[:, (0,2)] * [.1, ASPECT*.1] + .5
        dist = np.linalg.norm((self.uv[:,None,:]-CELLS)*[ASPECT,1], axis=2)
        self.owner = dist.argmin(axis=1)
        self.weight = np.exp(-((dist.min(axis=1)/.17)**2))
        self.random = np.random.default_rng(12).uniform(-1,1,(len(points),3)).astype(np.float32)
        # Each sample keeps its original texture RGB throughout the motion.
        outward = self.xyz - np.column_stack(((CELLS[self.owner,0]-.5)*10,
                           np.full(len(points),-.35),(CELLS[self.owner,1]-.5)*10/ASPECT))
        outward /= np.maximum(.1,np.linalg.norm(outward,axis=1))[:,None]
        speed = 1.35 + 1.65*np.abs(self.random[:,1])
        self.scatter = outward*speed[:,None]+self.random*[.92,2.2,.92]
        pink = (self.rgb[:,0]-self.rgb[:,1] > .18) & (self.rgb[:,0]-self.rgb[:,2] > .12)
        luminance = self.rgb @ np.array([.2126,.7152,.0722], dtype=np.float32)
        # Admission is based on the original relief, before any particle motion.
        self.relief = (-self.xyz[:,1] > .24) & ((luminance > .27) | pink)
        # Include bright, thin raised fibers outside the main cell bodies.
        flash_surface = self.relief | ((-self.xyz[:,1] > .12) & (luminance > .51))
        self.flash_uv = self.uv[flash_surface]
        self.xyz += self.random * [.019,.032,.019]
        x,y = np.rint(self.flash_uv*[WIDTH-1,HEIGHT-1]).astype(np.int32).T
        keep = (x>=4)&(x<WIDTH-4)&(y>=4)&(y<HEIGHT-4)
        index = y[keep]*WIDTH+x[keep]
        self.flash_mask = np.zeros(WIDTH*HEIGHT, dtype=bool)
        # Fill between adjacent samples from the source grid.
        for dy in range(-2,3):
            for dx in range(-2,3):
                self.flash_mask[index+dy*WIDTH+dx] = True

    def project(self, xyz, seconds):
        # Rotate real XYZ samples about the image axes with shallow perspective.
        yaw = .085 * math.sin(seconds*.43)
        pitch = .038 * math.sin(seconds*.33+.7)
        x,y,z = xyz.T
        x, y = x*math.cos(yaw)-y*math.sin(yaw), x*math.sin(yaw)+y*math.cos(yaw)
        y, z = y*math.cos(pitch)-z*math.sin(pitch), y*math.sin(pitch)+z*math.cos(pitch)
        scale = 1 / (1.05+y*.034)
        return np.column_stack((.5+x*scale*.1, .5+z*scale*ASPECT*.1))

    def render(self, seconds, delta, pupils, gaze, dwell, blink, pulse_age,
               burst=0., closed_for=0., quick_blinks=0):
        panel = np.zeros((HEIGHT,WIDTH,4), dtype=np.uint8)
        delta = np.clip(delta, -2, 2)
        # A small dead zone keeps the reference photo clear at rest.
        pupil_activity = np.clip((abs(delta)-.045)/.30, 0, 1)
        breath = math.sin(seconds*math.tau/3.2)*pupil_activity
        pupil_scale = 1 + delta*.055
        depth_scale = 1 + .48*breath + delta*.19
        xyz = self.xyz.copy()
        center = CELLS[self.owner]
        local_scale = (pupil_scale - 1 + breath*.095)*self.weight*self.relief
        xyz[:,0] += (self.uv[:,0]-center[:,0])*10*local_scale
        xyz[:,2] += (self.uv[:,1]-center[:,1])*10/ASPECT*local_scale
        xyz[:,1] *= 1 + (depth_scale-1)*self.relief
        drift = np.zeros(len(xyz))
        if gaze is not None and dwell >= 1.15:
            distance = np.linalg.norm((self.uv-gaze)*[ASPECT,1],axis=1)
            drift = np.clip((dwell-1.15)/1.35,0,1)*np.clip(1-distance/.095,0,1)
            xyz += self.random*drift[:,None]*(.45+.15*math.sin(seconds*15))
        uv = self.project(xyz, seconds)
        texture_strength = .72*pupil_activity*self.relief + .85*drift
        color = self.rgb*texture_strength[:,None]*(.24+.42*self.weight[:,None])
        color[self.relief] *= 1 + .43*breath
        flash = math.exp(-5.6*max(0,pulse_age-.055)) if 0 <= pulse_age < 1.05 else 0.
        if burst:
            scattered = xyz+self.scatter*burst
            projected = self.project(scattered, seconds)
            source_uv = self.uv if not pupil_activity and dwell < 1.15 else uv
            uv = source_uv*(1.-burst)+projected*burst
            textured_points = self.rgb*(.83+.44*np.abs(self.random[:,0:1]))
            if gaze is not None:
                focus = np.clip(1-np.linalg.norm((uv-gaze)*[ASPECT,1],axis=1)/.10,0,1)
                textured_points += focus[:,None]*(np.array([.04,1.,1.])-textured_points)
            if flash:
                pulse = (self.relief*flash)[:,None]
                textured_points = textured_points*(1-pulse)+pulse
            color = color*(1.-burst)+textured_points*burst
        pixels = np.rint(uv*[WIDTH-1,HEIGHT-1]).astype(np.int32)
        visible = (pixels[:,0]>=1)&(pixels[:,0]<WIDTH-1)&(pixels[:,1]>=1)&(pixels[:,1]<HEIGHT-1)
        x,y = pixels[visible].T
        rgb = np.clip(color[visible]*255,0,255).astype(np.uint8)
        flat = panel.reshape(-1,4)
        indices = y*WIDTH+x
        for offset in (-WIDTH,-1,1,WIDTH):
            np.maximum.at(flat[:,:3], indices+offset, rgb//3)
        np.maximum.at(flat[:,:3], indices, rgb)
        panel[:,:,3] = 255
        if flash:
            flat[self.flash_mask,3] = 255-round(222*flash*(1.-burst))
        draw_hud(panel, self.project(np.column_stack(((CELLS[:,0]-.5)*10,
                 np.full(len(CELLS),-.55),(CELLS[:,1]-.5)*10/ASPECT)),seconds),
                 pupil_scale, pupils, delta, dwell, blink, pulse_age,
                 burst, closed_for, quick_blinks)
        # The bottom row carries live controls for the finishing shader.
        panel[0,0] = [128+round(delta*63.5),128+round(breath*127),round(255*burst),255]
        watch = (0,0) if gaze is None else gaze
        panel[0,1] = [*(int(np.clip(a,0,1)*255) for a in watch),
                      int(np.clip((dwell-1.15)/1.35,0,1)*255),
                      255 if gaze is not None else 0]
        return panel


def draw_hud(panel, cells, scale, pupils, delta, dwell, blink, pulse_age,
             burst, closed_for, quick_blinks):
    def cyan(tone):
        return (round(tone*.04),tone,tone,0)

    def line(a,b,tone):
        length = 1+max(abs(b[0]-a[0]),abs(b[1]-a[1]))
        x = np.linspace(a[0], b[0], length).astype(int)
        y = np.linspace(a[1], b[1], length).astype(int)
        keep = (x>=0)&(x<WIDTH)&(y>=0)&(y<HEIGHT)
        panel[y[keep],x[keep]] = cyan(tone)

    def label(x,y,text,tone=255):
        ink = cyan(tone)
        for char in text:
            for row,bits in enumerate(GLYPHS.get(char,"00000")):
                for col in range(4):
                    px,py = x+col,y-row
                    if int(bits,16)&(8>>col) and 0<=px<WIDTH and 0<=py<HEIGHT:
                        panel[py,px] = ink
            x += 5

    readings = [f"{p:.2f}" if p > 0 else "--" for p in pupils]
    label(478,602,f"PUPIL L {readings[0]} MM / R {readings[1]} MM")
    label(478,592,f"SCALE = 1 + 0.055 * DP  /  DP {delta:+.2f} MM")
    label(478,582,f"BLINK {blink:04d}  DWELL {dwell:.2f} S"
          + ("  PULSE" if 0 <= pulse_age < 1.05 else ""))
    if burst > 0:
        label(478,572,f"EYES CLOSED {closed_for:.1f} / 3.0 S")
    elif quick_blinks:
        label(478,572,f"BLINK {quick_blinks} / 3")
    for i,(u,v) in enumerate(cells):
        x,y = int(u*WIDTH),int(v*HEIGHT)
        # Bracket the center; an open interior keeps the cell texture visible.
        for sx in (-1,1):
            for sy in (-1,1):
                corner = (x+sx*45,y+sy*32)
                line(corner,(corner[0]-sx*13,corner[1]),255)
                line(corner,(corner[0],corner[1]-sy*10),255)
        if any(p > 0 for p in pupils):
            start = (545+i*35,562)
            end = (x+(-45 if x>600 else 45), y+32)
            elbow = (end[0], end[1]+12)
            line(start,elbow,235)
            line(elbow,end,255)
        tx = min(x+49, WIDTH-100)
        label(tx,y+25,f"N{i+1:02d} {scale*100:05.1f}%")
        label(tx,y+15,f"X{u:.3f} Y{v:.3f}",224)
        label(tx,y+5,f"DP{delta:+.2f} MM",224)


def onCook(scriptOp):
    now = monotonic()
    _ = absTime.frame  # Register a time dependency even without a live sender.
    visual = scriptOp.parent()
    source = visual.parent().op("NEON_INPUT/neon_osc")

    def channel(name, default=0):
        chans = source.chans(name) or source.chans("/"+name)
        return float(chans[0][source.numSamples-1]) if chans and source.numSamples else default

    path = Path(visual.op("cloud_asset_path").text.strip())
    if not path.is_absolute():
        path = Path(project.folder) / path
    cloud = _clouds.get(path)
    if cloud is None:
        cloud = _clouds[path] = Cloud(read_cloud(path))
    state = scriptOp.fetch("signals", {}, search=False)
    clock = channel("clock", -1)
    session = channel("session")
    blink = int(channel("blink"))
    if state.get("version") != 4 or now < state["last"]:
        state = dict(session=session, blink=blink, clock=None, last=now,
                     start=now, delta=0, pulse=-100, version=4)
    elif session != state["session"]:
        state.update(session=session,blink=blink,clock=None,seen=-100,
                     blink_times=[],closed_at=None)
    if clock >= 0 and clock != state["clock"]:
        state.update(clock=clock, seen=now)
    fresh = now-state.get("seen",-100) < .3
    camera_parameters = visual.parent().par
    if getattr(camera_parameters,"Camerafollow",None) is not None and camera_parameters.Camerafollow.eval():
        if now >= state.get("next_camera_poll",0.):
            url = eye_stream_url(channel,fresh)
            if url != camera_parameters.Cameraurl.eval():
                camera_parameters.Cameraurl = url
            state["next_camera_poll"] = now+.5
    gaze = (channel("gx", .5), channel("gy", .5)) if fresh and channel("valid") else None
    lids = tuple(channel(name,-1) for name in ("aperture_l","aperture_r"))
    burst, closed_for = update_gesture(state,now,fresh,bool(channel("worn")),blink,lids)
    pupils = tuple(channel(name,-1) if fresh else -1 for name in ("pupil_l","pupil_r"))
    pupil_valid = any(p > 0 for p in pupils)
    dwell = channel("dwell") if gaze is not None else 0
    target = channel("pupil_delta") if pupil_valid else 0
    state["delta"] += (target-state["delta"])*(1-math.exp(-min(.10,now-state["last"])/.28))
    state.update(last=now,aperture=lids,burst_amount=burst,closed_for=closed_for,
                 gaze=gaze,dwell=dwell,pupil_valid=pupil_valid)
    scriptOp.store("signals", state)
    scriptOp.copyNumpyArray(cloud.render(now-state["start"],state["delta"],pupils,gaze,
                            dwell,
                            blink if fresh else 0,now-state["pulse"],burst,closed_for,
                            sum(now-stamp <= BLINK_WINDOW for stamp in state.get("blink_times", ()))))
