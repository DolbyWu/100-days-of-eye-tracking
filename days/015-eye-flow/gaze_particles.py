rng=np.random.default_rng()
heartbeat=-100.
last_clock=None
blink_sample = None
blink_times = []
pupil_fire = False
fire_started = 0.0
palette_index = 0
palette = [(201,226,52),(255,107,160),(59,225,255),(255,164,60),
           (179,135,255),(90,246,157),(255,100,84)]

def blink_colors(root):
    global blink_sample, palette_index, pupil_fire, fire_started
    osc = root.op('gaze_in')
    global heartbeat,last_clock
    clock=osc['clock'] if osc is not None else None
    if clock is not None and clock.eval()!=last_clock:
        last_clock=clock.eval()
        heartbeat=monotonic()
    count = osc['blink'] if osc is not None else None
    session = osc['session'] if osc is not None else None
    if count is not None:
        sample = (session.eval() if session is not None else None, int(count.eval()))
        if blink_sample is None or sample[0]!=blink_sample[0] or sample[1]<blink_sample[1]:
            blink_times.clear()
        if blink_sample is not None and sample[0] == blink_sample[0] and sample[1] > blink_sample[1]:
            palette_index = (palette_index + int(rng.integers(1,len(palette)))) % len(palette)
            now=monotonic()
            root.store("blink_sound_at",now)
            if sample[1]-blink_sample[1]==1:
                if blink_times and now-blink_times[-1]>.45:
                    blink_times.clear()
                blink_times.append(now)
                if len(blink_times)==3:
                    pupil_fire=not pupil_fire
                    fire_started=now
                    blink_times.clear()
            else:
                blink_times.clear()
        blink_sample = sample
    else:
        blink_sample = None
    rgb = palette[palette_index]
    return rgb, tuple(round(c*.80) for c in rgb), tuple(min(255,c+18) for c in rgb)

# Sample a moving toroidal volume once per video tick for both eyes.
fire_extent=3.35
axis=np.linspace(-fire_extent,fire_extent,208,dtype=np.float32)
fire_u,fire_v=np.meshgrid(axis,axis)
fire_frame=(-1,None)

# Heat is transported between frames. A jet feeds one patch of the ring;
# a group of sparks inherits that jet's heading and speed at birth.
heat_field=np.zeros_like(fire_u)
grid_y,grid_x=np.indices(heat_field.shape,dtype=np.float32)
field_radius=np.maximum(.01,np.hypot(fire_u,fire_v))
nx,ny=fire_u/field_radius,fire_v/field_radius
jets=[]
sparks=[]
fire_rng=np.random.default_rng()
# Wrapped eddies have no angular seam; both the fuel bed and the
# visible folds travel through the same irregular temperature pattern.
def make_eddy_map():
    atlas=np.zeros((256,256),np.float32)
    for cells,weight in ((8,.55),(16,.28),(32,.12),(64,.05)):
        grid=fire_rng.uniform(-1,1,(cells,cells)).astype(np.float32)
        padded=np.pad(grid,2,mode='wrap')
        step=256//cells
        smooth=cv2.resize(padded,None,fx=step,fy=step,interpolation=cv2.INTER_CUBIC)
        atlas+=weight*smooth[2*step:2*step+256,2*step:2*step+256]
    return atlas

eddies=make_eddy_map()
def sample_eddies(x,y):
    return cv2.remap(eddies,x.astype(np.float32,copy=False),y.astype(np.float32,copy=False),cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)

next_jet=0.
heat_time=-1.

def scatter_flames(rgb,opacity,t,size):
    global heat_field,next_jet,heat_time
    if heat_time<0 or t<heat_time or t-heat_time>1:
        heat_field.fill(0)
        jets.clear()
        sparks.clear()
        next_jet=t
    dt=min(.09,max(1/30,t-heat_time))
    heat_time=t
    if t>=next_jet:
        angle=fire_rng.uniform(-np.pi,np.pi)
        for _ in range(fire_rng.integers(2,6)):
            heading=angle+fire_rng.normal(0,.23)
            speed=fire_rng.uniform(1.5,4)
            turn=fire_rng.uniform(-1,1)
            c,s=np.cos(heading),np.sin(heading)
            jets.append((t,fire_rng.uniform(.13,.46),c,s,fire_rng.uniform(.09,.24),speed,turn))
            for _ in range(fire_rng.integers(1,4)):
                sparks.append((t,c*1.6,s*1.6,c*speed-s*turn,s*speed+c*turn,
                               fire_rng.uniform(.17,.53)))
        next_jet=t+fire_rng.uniform(.12,.43)
    jets[:]=[j for j in jets if t-j[0]<j[1]]
    swing=np.sin(4*fire_v-4*t+1.3*np.sin(3*fire_u+2*t))
    twist=.56*swing+.19*np.sin(12*fire_u+8*fire_v-7*t)
    vx=.95*nx-ny*twist
    vy=.95*ny+nx*twist-.48
    scale=(len(axis)-1)/(2*fire_extent)
    fuel=sample_eddies(39*fire_u+12*t+8*swing,41*fire_v-7*t+11*twist)
    bed=np.exp(-((field_radius/size-1.16-.16*fuel)/.25)**2)
    heat_field+=dt*bed*np.clip(1.15+3.3*fuel,.12,3.5)
    for birth,life,c,s,width,speed,turn in jets:
        radial=fire_u*c+fire_v*s
        cross=fire_v*c-fire_u*s
        force=np.exp(-((cross-turn*.15*(radial-1.5))/(width*1.9))**2
                     -((radial-1.75)/.72)**2)
        vx+=force*c*speed
        vy+=force*s*speed
        source=np.exp(-((radial-1.32*size)/.32)**2-(cross/width)**2)
        heat_field+=source*min(1,(t-birth+.03)*20)*dt*11
    heat_field=cv2.remap(heat_field,grid_x-vx*dt*scale,grid_y-vy*dt*scale,
                         cv2.INTER_LINEAR)*np.exp(-dt*2.3)
    np.minimum(heat_field,1.8,out=heat_field)
    # Break cooler shear layers into thin, luminous folds.
    fold=np.sin(11*fire_u+5*fire_v-4*t+2.4*swing)
    temperature=heat_field*(1+.36*fold+.16*np.sin(21*fire_v-6*t+3*fold))
    h=np.clip(temperature*1.35,0,1)
    alpha=np.clip(temperature*2.7-.055,0,.98)
    rgb[:,:,0]=(78+177*np.minimum(1,h*2.6))*alpha
    rgb[:,:,1]=(9+231*h**1.65)*alpha
    rgb[:,:,2]=(2+101*h**4)*alpha
    opacity[:]=alpha
    sparks[:]=[s for s in sparks if t-s[0]<s[5]]
    for birth,x,y,dx,dy,life in sparks:
        age=t-birth
        fraction=age/life
        x+=dx*age
        y+=dy*age-.8*age*age
        start=(round((x+fire_extent)*scale),round((y+fire_extent)*scale))
        end=(round(start[0]-dx*scale*.035),round(start[1]-(dy-1.6*age)*scale*.035))
        light=(1-fraction)**.8
        cv2.line(rgb,start,end,(251*light,165*light**2,53*light**3),1)
        cv2.line(opacity,start,end,float(light),1)

def fire_volume(age):
    global fire_frame
    tick=int(age*30)
    if fire_frame[0]==tick:
        return fire_frame[1]
    t=tick/30
    impact=min(1,t*12)*np.exp(-max(0,t-.09)*5)
    size=.91+.25*impact+.09*min(1,t*7)
    u,v=fire_u/size,fire_v/size
    angle=np.arctan2(v,u)
    radial=np.hypot(u,v)
    # Large traveling lobes break the silhouette. Smaller curls fold the
    # luminous sheet over itself at different depths.
    wave=3*angle-1.8*t+.85*np.sin(2*angle+1.2*t)
    rim=1.19+.035*np.sin(wave)+.035*np.cos(7*angle+t+np.sin(wave))
    width=.49+.025*np.cos(wave-.8)+.03*np.sin(5*angle-2*t)
    rgb=np.zeros((*u.shape,3),np.float32)
    opacity=np.zeros_like(u)
    scatter_flames(rgb,opacity,t,size)
    # Compress the visible spray outside the rim while the heat field
    # continues to drive the original folds through the ring.
    outside=np.maximum(field_radius-1.68*size,0)
    offset=outside*(1/.55-1)*(len(axis)-1)/(2*fire_extent)
    map_x=(grid_x+nx*offset).astype(np.float32)
    map_y=(grid_y+ny*offset).astype(np.float32)
    rgb=cv2.remap(rgb,map_x,map_y,cv2.INTER_LINEAR)
    opacity=cv2.remap(opacity,map_x,map_y,cv2.INTER_LINEAR)
    longitude=angle*(256/(2*np.pi))
    warp=sample_eddies(longitude,45*radial+9*t)
    plume=np.minimum(heat_field,1.25)
    # Slice from the far wall towards the viewer. A slight tilt exposes
    # the lip at the bottom of the image and the recess behind it.
    for z in (-.56,-.42,-.28,-.14,0,.14,.28,.42,.56):
        local_v=(v+.23*z)/.97
        d=np.hypot(u,local_v)-rim
        section=np.arctan2(z,d)
        # A constant phase travels from the underside (negative angle),
        # over the crown (pi/2), to the inner wall (pi).
        flow=section-2.45*t
        latitude=flow*(256/(2*np.pi))
        billow=sample_eddies(longitude+19*warp+9*z,latitude+24*warp)
        fine=sample_eddies(2*longitude+28*billow,latitude+44*billow)
        filament=np.clip(1-abs(fine+.42*billow)*3.6,0,1)**2
        crest=np.clip(.37+.86*billow+.35*fine+.39*plume,0,1)
        inward=np.clip(-d/.48,0,1)
        reach=.16*inward*crest**2
        dist=np.hypot(d,z)
        density=np.clip((width+.19*billow+.07*fine+.08*plume+reach-dist)*9,0,1)*(.30+.63*crest)
        # Keep the recessed wall ember-red and light the raised folds.
        front=np.clip(z/.48,0,1)
        shadow=inward*(1-front)
        heat=np.clip(.08+.57*crest+.24*filament+.16*front
                     -.28*shadow+.19*plume+.16*impact,0,1)
        emission=np.stack((32+223*np.minimum(1,heat*1.9),
                           2+244*heat**2.55,2+112*heat**6),axis=-1)
        rgb+=(emission-rgb)*density[...,None]
        opacity+=(1-opacity)*density
    glow=np.exp(-((radial-rim)/.66)**2)*.21
    rgb+=glow[...,None]*np.array([120,30,4],np.float32)
    fade=min(1,t*15)
    rgba=np.dstack((np.minimum(255,rgb)*fade,255*np.maximum(opacity,glow)*fade)).astype(np.uint8)
    fire_frame=(tick,rgba)
    return rgba

def draw_fire_ring(canvas,left,top,right,bottom,now):
    cx,cy=(right+left)/2,(top+bottom)/2
    hw=hh=max(1,round(np.sqrt((right-left)*(bottom-top))*fire_extent/2))
    x,y=round(cx)-hw,round(cy)-hh
    x0,x1=max(0,x),min(canvas.shape[1],x+2*hw)
    y0,y1=max(0,y),min(canvas.shape[0],y+2*hh)
    if x1<=x0 or y1<=y0:
        return
    ring=cv2.resize(fire_volume(max(0,now-fire_started)),(2*hw,2*hh))
    ring=ring[y0-y:y1-y,x0-x:x1-x]
    patch=canvas[y0:y1,x0:x1]
    patch[:]=np.minimum(255,patch*(1-ring[:,:,3:4]/255.)+ring[:,:,:3])

def pupil_detail(canvas,box,scale,root,now):
    x,y,a,b=box
    left,top,right,bottom=[round(v*scale) for v in (x,y,x+a,y+b)]
    if pupil_fire and right > left and bottom > top:
        draw_fire_ring(canvas,left,top,right,bottom,now)
    osc=root.op('gaze_in')
    side='l' if left<canvas.shape[1]/2 else 'r'
    ch=osc['pupil_'+side]
    valid=osc['valid']
    mm=ch.eval() if ch is not None and valid is not None and valid.eval()==1 and now-heartbeat<.45 else -1
    label=f'{mm:.2f} mm' if mm>0 else '-- mm'
    at=(max(0,min(canvas.shape[1]-65,left)),max(15,top-6))
    cv2.putText(canvas,label,at,cv2.FONT_HERSHEY_SIMPLEX,.44,(25,25,25),2,cv2.LINE_AA)
    cv2.putText(canvas,label,at,cv2.FONT_HERSHEY_SIMPLEX,.44,(245,245,245),1,cv2.LINE_AA)
