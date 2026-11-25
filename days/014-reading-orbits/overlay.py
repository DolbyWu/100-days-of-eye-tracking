import cv2
import numpy as np
from time import monotonic

def onCook(scriptOp):
    state=parent().op('reading_source').module.state()
    mask=state.get('mask')
    layer=np.zeros((720,1280,4),np.uint8)
    if mask is not None:
        # Premultiplied ink over a displaced, dark drop shadow.
        under=np.zeros_like(mask)
        under[2:,1:]=mask[:-2,:-1]
        under=cv2.multiply(under,255-mask,scale=.85/255)
        layer[:,:,3]=cv2.add(mask,under)
        for c,tint in enumerate((255,247,224)):
            layer[:,:,c]=cv2.addWeighted(mask,tint/255,under,.025,0)
    page=state.get('page')
    if page is not None:
        now=monotonic()
        for figure in getattr(page,'figures',()):
            figure.paint(layer,now)
    osc=parent().op('neon_osc')
    def value(name):
        channels=osc.chans(name) or osc.chans('/'+name)
        return float(channels[0][osc.numSamples-1]) if channels and osc.numSamples else None
    connected=monotonic()-state.get('heartbeat',0)<.7
    valid=connected and value('valid')==1
    def measurement(name,unit='',precision=2):
        v=value(name)
        return f"{v:.{precision}f}{unit}" if valid and v is not None and v>=0 else '--'
    gx,gy=value('gx'),value('gy')
    gaze=f"{gx:.2f}  {gy:.2f}" if valid and gx is not None and gy is not None else '--'
    blink=value('blink')
    items=[
        ('PUPIL L',measurement('pupil_l',' mm')),
        ('PUPIL R',measurement('pupil_r',' mm')),
        ('GAZE X / Y',gaze),
        ('GAZE SPEED',measurement('speed',precision=2)),
        ('BLINKS',str(int(blink)) if connected and blink is not None and blink>=0 else '--'),
        ('TRACKING','LIVE' if valid else 'WAITING'),
    ]
    x,y,w,h=22,22,250,224
    layer[y:y+h,x:x+w,:3]=0
    layer[y:y+h,x:x+w,3]=190
    cv2.rectangle(layer,(x,y),(x+w,y+h),(170,230,230,235),1,cv2.LINE_AA)
    cv2.putText(layer,'NEON / LIVE DATA',(x+13,y+25),cv2.FONT_HERSHEY_SIMPLEX,.48,(180,245,245,255),1,cv2.LINE_AA)
    cv2.line(layer,(x+13,y+34),(x+w-13,y+34),(100,190,190,210),1,cv2.LINE_AA)
    for i,(label,text) in enumerate(items):
        yy=y+57+i*27
        cv2.putText(layer,label,(x+13,yy),cv2.FONT_HERSHEY_SIMPLEX,.36,(115,190,190,230),1,cv2.LINE_AA)
        cv2.putText(layer,text,(x+132,yy),cv2.FONT_HERSHEY_SIMPLEX,.41,(180,245,245,255),1,cv2.LINE_AA)
    scriptOp.copyNumpyArray(np.ascontiguousarray(layer[::-1]))
