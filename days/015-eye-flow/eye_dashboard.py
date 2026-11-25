import cv2
import numpy as np
from time import monotonic

last_clock = None
last_packet = last_flash = -100.
previous = None

def onCook(scriptOp):
    global last_clock, last_packet, last_flash, previous
    _ = absTime.frame
    osc = scriptOp.parent().op('gaze_in')
    now = monotonic()
    def value(name):
        channel = osc[name]
        if channel is not None:
            v = float(channel.eval())
            if np.isfinite(v):
                return v
        return None

    clock = value('clock')
    if clock is not None and clock != last_clock:
        last_packet = now
    last_clock = clock
    live = now-last_packet < .55
    count = value('blink') if live else None
    session = value('session')
    if count is not None and previous is not None and session == previous[0] and count > previous[1]:
        last_flash = now
    previous = (session,count) if count is not None else None
    valid = value('valid') == 1
    def fmt(key, digits=2, gaze=False, nonnegative=False):
        v = value(key)
        if not live or v is None or (gaze and not valid) or (nonnegative and v < 0):
            return '--'
        return f'{v:.{digits}f}'
    def group(prefix, axes):
        return '  '.join(fmt(prefix+'_'+axis) for axis in axes)
    def pair(left,right,**opts):
        return fmt(left,**opts)+'  /  '+fmt(right,**opts)

    card = np.empty((154,1248,4),np.uint8)
    card[:] = (9,17,22,210)
    def label(text,x,y,accent=False):
        color=(110,239,219,255) if accent else (237,243,245,255)
        cv2.putText(card,text,(x,y),cv2.FONT_HERSHEY_SIMPLEX,.46,color,1,cv2.LINE_AA)
    columns = [
        ('EYES', [
            'Pupil L/R mm   '+pair('pupil_l','pupil_r',gaze=True,nonnegative=True),
            'Lid L/R mm     '+pair('aperture_l','aperture_r',nonnegative=True),
            'Pupil delta mm   '+fmt('pupil_delta',gaze=True),
            'Blinks   '+fmt('blink',0)]),
        ('GAZE & EVENTS', [
            'X / Y   '+pair('gx','gy',gaze=True),
            'Vx / Vy   '+pair('vx','vy',gaze=True),
            'Speed   '+fmt('speed',gaze=True),
            'Fixations / onsets   '+pair('fixation','fixation_onset',digits=0),
            'Saccades / onsets   '+pair('saccade','saccade_onset',digits=0)]),
        ('HEAD MOTION', [
            'Accel XYZ   '+group('accel_data','xyz'),
            'Gyro XYZ   '+group('gyro_data','xyz'),
            'Quat XY   '+group('quaternion','xy'),
            'Quat ZW   '+group('quaternion','zw'),
            'IMU time   '+fmt('imu_t')+' s']),
        ('NEON  /  '+('LIVE' if live else 'OFFLINE'), [
            'Gaze valid   '+fmt('valid',0),
            'Scene frame   '+fmt('scene_frame',0,nonnegative=True),
            'Gaze time   '+fmt('gaze_t')+' s',
            'Session   '+fmt('session',0),
            'Bridge clock   '+fmt('clock')])]
    for i,(heading,rows) in enumerate(columns):
        x=12+310*i
        label(heading,x,20,True)
        for j,row in enumerate(rows):
            label(row,x,45+23*j)
    if live and now-last_flash < .32:
        cv2.circle(card,(175,109),5,(110,239,219,255),-1,cv2.LINE_AA)
    scriptOp.copyNumpyArray(np.ascontiguousarray(card[::-1]))
