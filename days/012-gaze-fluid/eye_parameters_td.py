"""TouchDesigner Script TOP: live eye-video detections packed into seven RGBA texels."""
import numpy as np


def onCook(scriptOp):
    source=scriptOp.parent().parent().op('NEON_INPUT/neon_osc')
    def channel(name,default=0):
        ch=source.chans(name) or source.chans('/'+name)
        return float(ch[0][source.numSamples-1]) if ch and source.numSamples else default
    values=[]
    for prefix in ('eye_l','eye_r'):
        values.append((channel(prefix+'_x'),channel(prefix+'_y'),
                       channel(prefix+'_radius'),channel(prefix+'_valid')))
    for i in range(3):
        prefix='eye_change'+str(i)
        valid=channel(prefix+'_valid')
        values.append((channel(prefix+'_x'),channel(prefix+'_y'),
                       channel(prefix+'_w') if valid else 0,
                       channel(prefix+'_h') if valid else 0))
    values.append((channel('pupil_l',-1),channel('pupil_r',-1),
                   channel('blink'),channel('eye_video_valid')))
    values.append(tuple(channel('eye_change'+str(i)+'_value') for i in range(3))+(0,))
    scriptOp.copyNumpyArray(np.asarray([values],dtype=np.float32))
