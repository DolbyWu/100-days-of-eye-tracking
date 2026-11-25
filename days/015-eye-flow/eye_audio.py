from time import monotonic
import numpy as np

rate = 0
cursor = 0
last_blink = None
blink_offset = 0
level = 0.

def prepare(sample_rate):
    global rate, fire, blink, blink_offset, cursor
    rate = sample_rate
    rng = np.random.default_rng(1515)
    n = round(rate*6)
    hz = np.fft.rfftfreq(n, 1/rate)
    noise = np.fft.rfft(rng.normal(size=(2,n)),axis=1)
    band = (hz/(hz+45))/(1+(hz/460)**2)
    fire = np.fft.irfft(noise*band,n=n,axis=1)
    fire *= .055/fire.std()
    for _ in range(70):
        start = rng.integers(n)
        t = np.arange(round(rate*rng.uniform(.008,.04)))/rate
        crack = rng.uniform(.05,.19)*np.exp(-t*190)*rng.normal(size=t.size)
        fire[rng.integers(2),(start+np.arange(t.size))%n] += crack
    t = np.arange(round(rate*.105))/rate
    blink = .30*(1-np.exp(-t*850))*np.exp(-t*57)*np.sin(2*np.pi*(1250*t-3400*t*t))
    blink_offset = blink.size
    cursor = 0

def onCook(scriptOp):
    global cursor,last_blink,blink_offset,level
    clock = scriptOp.inputs[0]
    if rate != clock.rate:
        prepare(clock.rate)
    n = clock.numSamples
    if not n:
        scriptOp.clear()
        return
    root = scriptOp.parent()
    now = monotonic()
    visible = root.op('out_eye_flow').fetch('fire_visible_at',-1,search=False)
    target = float(0 <= now-visible < .35)
    gain = target+(level-target)*np.exp(-np.arange(1,n+1)/(rate*.07))
    level = gain[-1]
    out = fire[:,(cursor+np.arange(n))%fire.shape[1]]*gain
    cursor += n
    event = root.fetch('blink_sound_at',None,search=False)
    if event != last_blink and event is not None and 0 <= now-event < .3:
        blink_offset = 0
    last_blink = event
    k = min(n,blink.size-blink_offset)
    out[:,:k] += blink[blink_offset:blink_offset+k]
    blink_offset += k
    scriptOp.copyNumpyArray(np.ascontiguousarray(np.tanh(out),dtype=np.float32),baseName='audio')
    scriptOp.rate = rate
    scriptOp.start = clock.start
