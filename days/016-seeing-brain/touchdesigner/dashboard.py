import json
from math import cos, radians, sin
dashboard_clock=None
dashboard_seen=-1e9
dashboard_centers=None

def draw_dashboard(img,r,now):
    global dashboard_clock,dashboard_seen,dashboard_centers
    h,w=img.shape[:2]
    features=r.op('features')
    module=r.op('features_source').module
    engine=module.engine
    if engine is None:return
    mock=bool(r.par.Mock)
    if mock:
        packet=module.demo(absTime.seconds)
        live=True
    else:
        osc=r.op('neon')
        packet={c.name:c.eval() for c in osc.chans()}
        clock=packet.get('clock')
        if clock is not None and clock!=dashboard_clock:
            dashboard_clock,dashboard_seen=clock,now
        live=now-dashboard_seen<.55
    def val(key,digits=2):
        v=packet.get(key)
        if not live or v is None or not np.isfinite(v):return '--'
        if key in ('gx','gy','vx','vy','speed','pupil_delta','pupil_l','pupil_r') and not packet.get('valid'):return '--'
        if key in ('aperture_l','aperture_r','scene_frame','pupil_l','pupil_r') and v<0:return '--'
        return f'{v:.{digits}f}'
    def fields(*keys,digits=2):
        return ' / '.join(val(k,digits) for k in keys)
    k=min(w/960,h/540)
    x=w-round(300*k); bottom=h-round(20*k)
    event,until=r.fetch('trigger',('',0))
    state=event if now<until else ('blink' if now<engine.flash_until else engine.event)
    rows=[
        ('Pupil L/R mm',fields('pupil_l','pupil_r'),'Lid L/R mm',fields('aperture_l','aperture_r')),
        ('Pupil delta',val('pupil_delta'),'Blinks',val('blink',0)),
        ('Gaze XY',fields('gx','gy'),'Velocity XY',fields('vx','vy')),
        ('Speed',val('speed'),'Valid',val('valid',0)),
        ('Fix / onset',fields('fixation','fixation_onset',digits=0),'Sac / onset',fields('saccade','saccade_onset',digits=0)),
        ('Accel XYZ',fields(*['accel_data_'+a for a in 'xyz'],digits=1),'Gyro XYZ',fields(*['gyro_data_'+a for a in 'xyz'],digits=1)),
        ('Quat XY',fields('quaternion_x','quaternion_y'),'Quat ZW',fields('quaternion_z','quaternion_w')),
        ('Gaze time',val('gaze_t',1),'IMU time',val('imu_t',1)),
        ('Scene frame',val('scene_frame',0),'Session',val('session',0)),
        ('Bridge clock',val('clock',1),'State',(state or 'idle').replace('smooth_motion','smooth motion'))]
    if dashboard_centers is None:dashboard_centers=json.loads(r.op('landmarks').text)
    active={}
    for key,center in dashboard_centers.items():
        c=features['activation_'+key]
        if c is None:continue
        suffix=key.replace('_','').lower()
        level=max(float(c),getattr(r.par,'Emit'+suffix).eval())*getattr(r.par,'Gain'+suffix).eval()
        if level>.055:active.setdefault(key.rsplit('_',1)[0] if key.endswith(('_L','_R')) else key,[]).append((key,center,level))
    step=round(13*k)
    top=bottom-step*(len(rows)+len(active)+2)-round(9*k)
    left=x+round(6*k)
    cv2.rectangle(img,(x,top),(w-round(6*k),bottom),(9,15,21,218),-1)
    def text(s,xx,yy,color=(215,229,235,255),size=.285):
        cv2.putText(img,s,(xx,yy),cv2.FONT_HERSHEY_SIMPLEX,size*k,color,1,cv2.LINE_AA)
    text('NEON   '+('DEMO' if mock else 'LIVE' if live else 'OFFLINE'),left,top+step,(134,236,225,255),.34)
    for i,row in enumerate(rows):
        yy=top+(i+2)*step
        for j in range(2):
            xx=left+round(j*148*k)
            text(row[2*j],xx,yy)
            text(row[2*j+1],xx+round(58*k),yy)
    start=top+(len(rows)+3)*step
    az=radians(r.par.Azimuth.eval()-r.op('anatomy_transform').par.ry.eval())
    el=radians(r.par.Elevation.eval())
    scale=r.op('anatomy_transform').par.scale.eval()*w/r.op('orbit').par.orthowidth.eval()
    for i,(region,items) in enumerate(sorted(active.items())):
        yy=start+i*step
        for key,(xx,up,zz),level in items:
            px=round(w/2+scale*(cos(az)*xx-sin(az)*zz))
            py=round(h/2-scale*(cos(el)*up-sin(el)*(sin(az)*xx+cos(az)*zz)))
            color=(250,179,96,175)
            cv2.line(img,(px,py),(x-2,yy-3),color,1,cv2.LINE_AA)
            cv2.circle(img,(px,py),2,color,1,cv2.LINE_AA)
        names=' / '.join(it[0] for it in items)
        note={'V1':'visual cortex','FEF':'frontal eye field','SC':'superior colliculus','LGN':'visual relay','IPS':'parietal sulcus','MT_MST':'motion proxy','brainstem':'blink network','cerebellum':'motor coordination'}.get(region,'')
        text(f'{names}   {max(it[2] for it in items):.2f}   {note}',left,yy,(255,196,129,255))
