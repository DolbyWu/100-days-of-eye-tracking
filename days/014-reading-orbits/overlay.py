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
    scriptOp.copyNumpyArray(np.ascontiguousarray(layer[::-1]))
