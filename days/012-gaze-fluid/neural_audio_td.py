"""Stereo synthesis driven by the same event times as the Day 12 visuals."""
import math
from time import monotonic

import numpy as np

TAU = 2 * math.pi
_engines = {}


def envelope(t, attack, release, end):
    return np.clip(t/attack, 0, 1) * np.exp(-release*t) * np.clip((end-t)/.04, 0, 1)


def cue_sound(kind, rate):
    """Make short, softened electronic transients and granular textures."""
    seconds = {"gaze":.17, "blink":.29, "dissolve":.52,
               "burst":1.35, "regroup":1.1, "restored":.39}[kind]
    t = np.arange(round(rate*seconds))/rate
    sine = lambda hz: np.sin(TAU*hz*t)
    rng = np.random.default_rng(1212)
    noise = rng.normal(0.,1.,len(t)+15)
    noise = np.convolve(noise,np.ones(16)/16,"valid")
    if kind == "gaze":
        signal = .64*sine(695)+.22*sine(1055)+.09*sine(1635)
        return .13*envelope(t,.009,26,seconds)*signal
    if kind == "blink":
        signal = .48*np.sin(TAU*(138*t+14*(1-np.exp(-23*t)))) + .32*sine(307)+.65*noise
        return .19*envelope(t,.008,13,seconds)*signal
    if kind == "dissolve":
        signal = (.48*sine(721)+1.55*noise)*(.45+.55*sine(19)**2)
        return .10*envelope(t,.045,3.1,seconds)*signal
    if kind == "burst":
        bass = np.sin(TAU*(47*t+2.4*(1-np.exp(-8*t))))*np.exp(-8*t)
        signal = .58*bass+.38*sine(283)*np.exp(-5*t)+1.35*noise*(.40+.60*sine(13)**2)
        return .30*envelope(t,.009,2.6,seconds)*signal
    if kind == "regroup":
        sweep = np.sin(TAU*(188*t+192*t*t))
        signal = .48*sweep+.15*np.sin(TAU*(310*t+271*t*t))+.3*noise
        rise = np.sin(np.pi*t/seconds)**1.7
        return .12*rise*signal
    return .13*envelope(t,.016,8,seconds)*(.55*sine(329.6)+.33*sine(493.9)+.15*sine(659.2))


class Synth:
    def __init__(self, rate):
        self.rate = rate
        self.phase = 0.
        self.mod_phase = 0.
        self.bed = 0.
        self.pitch = 122.
        self.level = 0.
        self.voices = []
        self.cues = {}
        self.events = {}
        self.last_point = None
        self.last_tick = -math.inf
        self.dissolving = False
        self.was_regrouping = False
        self.last_session = None
        self.played = {}

    def play(self, kind, pan=0., start=0):
        if kind not in self.cues:
            self.cues[kind] = cue_sound(kind,self.rate)
        self.voices.append((self.cues[kind],max(0,start),max(-.8,min(.8,pan))))
        self.played[kind] = self.played.get(kind,0)+1

    def update(self, now, state):
        # If the visuals stop cooking, release the ambience and discard stale edges.
        if now-state.get("last",-math.inf) >= .35:
            self.last_point = None
            self.dissolving = False
            return 0.,0.,0.
        gaze = state.get("gaze")
        pan = (2*gaze[0]-1)*.72 if gaze is not None else 0.
        new_session = state.get("session") != self.last_session
        self.last_session = state.get("session")
        if gaze is None:
            self.last_point = None
        elif now-self.last_tick > .145 and (
            self.last_point is None or math.dist(gaze,self.last_point) > .060
        ):
            self.play("gaze",pan)
            self.last_point = gaze
            self.last_tick = now
        for event, kind in (("pulse","blink"),("burst","burst"),("regroup","regroup")):
            stamp = state.get(event)
            if stamp is not None and stamp != self.events.get(event):
                age = now-stamp
                if 0 <= age < .30 and (not new_session or age < .06):
                    if kind != "blink" or stamp != state.get("burst"):
                        self.play(kind,pan if kind == "blink" else 0., round(age*self.rate))
            self.events[event] = stamp
        regrouping = state.get("regroup") is not None
        if self.was_regrouping and not regrouping and state.get("burst") is None:
            self.play("restored")
        self.was_regrouping = regrouping
        dissolving = gaze is not None and state.get("dwell",0.) >= 1.15
        if dissolving and not self.dissolving:
            self.play("dissolve",pan)
        self.dissolving = dissolving
        delta = max(-2.,min(2.,state.get("delta",0.)))
        pupil = max(0.,min(1.,(abs(delta)-.045)/.37)) if state.get("pupil_valid") else 0.
        return delta,pupil,state.get("burst_amount",0.)

    def render(self, n, now, state, volume):
        delta,pupil,scatter = self.update(now,state)
        samples = np.arange(1,n+1)
        target_pitch = 122.*2**(.39*delta)
        target_bed = .042*pupil*(1-.55*scatter)
        bed_slew = np.exp(-samples/(.14*self.rate))
        bed = target_bed+(self.bed-target_bed)*bed_slew
        pitch = target_pitch+(self.pitch-target_pitch)*bed_slew
        carrier = self.phase+TAU*np.cumsum(pitch)/self.rate
        modulation = self.mod_phase+TAU*samples*.76/self.rate
        fm = .30+.75*pupil
        left = bed*(np.sin(carrier+fm*np.sin(2*carrier))+.25*np.sin(carrier*2+modulation))
        right = bed*(np.sin(carrier+fm*np.sin(2*carrier))+.25*np.sin(carrier*2-modulation))
        self.bed,self.pitch = float(bed[-1]),float(pitch[-1])
        self.phase,self.mod_phase = carrier[-1]%TAU,modulation[-1]%TAU
        voices = []
        for sound,offset,pan in self.voices:
            count = min(n,len(sound)-offset)
            if count <= 0:
                continue
            segment = sound[offset:offset+count]
            left[:count] += segment*math.sqrt(.5-.5*pan)
            right[:count] += segment*math.sqrt(.5+.5*pan)
            if offset+count < len(sound):
                voices.append((sound,offset+count,pan))
        self.voices = voices
        gain = volume+(self.level-volume)*np.exp(-samples/(.025*self.rate))
        self.level = float(gain[-1])
        return np.asarray(.8*np.tanh(np.stack((left,right))*gain),dtype=np.float32)


def onCook(scriptOp):
    clock = scriptOp.inputs[0]
    scriptOp.rate = clock.rate
    scriptOp.start = clock.start
    count = clock.numSamples
    if count < 1:
        scriptOp.clear()
        return
    component = scriptOp.parent().parent()
    cloud = component.op("VISUAL_RENDER/neural_cloud")
    state = cloud.fetch("signals",{},search=False) if cloud is not None else {}
    engine = _engines.get(scriptOp.path)
    if engine is None or engine.rate != clock.rate:
        engine = _engines[scriptOp.path] = Synth(clock.rate)
    volume = float(component.par.Soundvolume.eval()) if component.par.Soundenabled.eval() else 0.
    audio = engine.render(count,monotonic(),state,volume)
    scriptOp.copyNumpyArray(audio,baseName="audio")
    scriptOp.rate = clock.rate
    scriptOp.start = clock.start
    scriptOp.store("audio_status", dict(events=engine.played.copy(),
                   peak=float(np.abs(audio).max()), frames=count))
