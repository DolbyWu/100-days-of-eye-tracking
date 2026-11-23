from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_state={}


def enter_key():
    prompt='text returned of (display dialog "OpenAI API key for this TouchDesigner session" default answer "" with hidden answer buttons {"Cancel", "Use Key"} default button "Use Key")'
    dialog=subprocess.run(['/usr/bin/osascript','-e',prompt],capture_output=True,text=True)
    return dialog.stdout.strip() if dialog.returncode==0 else ''


def camera_urls(folder,host):
    candidates=(folder.parents[2]/'touchdesigner',folder.parent/'012-gaze-fluid',folder)
    for path in candidates:
        python=path/'.venv/bin/python'
        if python.is_file():
            result=subprocess.run([str(python),str(folder/'cameras.py'),host],capture_output=True,timeout=12)
            if result.returncode==0: return json.loads(result.stdout)
    return {}


def state():
    if not _state:
        _state.update(pool=ThreadPoolExecutor(max_workers=2),handles=EyeHandles(),key='',job=None,keyjob=None,
                      page=None,registration=None,request=False,status='Aim Neon at a page, then press Scan Page.',
                      mode=None,clock=None,heartbeat=-100,last=monotonic(),scan=0,align=0,world_seen=0)
    return _state


def action(name):
    s=state()
    if name=='Resetreading':
        page=s['page']
        if page is not None:
            page.motes.clear()
            page.candidate=None
            page.since=0
            for figure in page.figures:
                figure.birth=None
            s['loaded']=monotonic()
        return
    if name=='Enterkey' and not s['keyjob']:
        s['keyjob']=s['pool'].submit(enter_key)
    elif name=='Importpage' and not s['job']:
        r=op('/project1/day14_reading')
        mode=r.par.Reader.eval()
        if mode=='OpenAI' and not s['key']:
            s['status']='Enter API Key first, or choose Apple Vision.'
            return
        r.par.Autopages=False
        if r.par.Demo.eval(): s.update(page=None,registration=None)
        r.par.Demo=False
        s.update(mode=False,request=False,pending_image=None,observed=None,pending_signature=[])
        s['generation']=s.get('generation',0)+1
        s['jobgen']=s['generation']
        s['job']=s['pool'].submit(read_reference,Path(project.folder),mode,s['key'])
        s['status']='Choose reference page…'
    elif name=='Scan' and not s['job']:
        s['request']=True


def scene_image(root):
    cam=root.op('book_camera')
    if cam.width<200 or cam.height<160 or not root.par.Sceneurl.eval(): return None
    image=cam.numpyArray(delayed=False)
    if image is None: return None
    bgr=np.ascontiguousarray(np.clip(image[::-1,:,2::-1]*255,0,255).astype('uint8'))
    return bgr if bgr[::12,::12].std()>6 else None


def onCook(scriptOp):
    _=absTime.frame
    r=scriptOp.parent()
    s=state()
    now=monotonic()
    demo=bool(r.par.Demo.eval())
    folder=Path(project.folder)
    osc=r.op('neon_osc')
    def ch(name,default=-1):
        channels=osc.chans(name) or osc.chans('/'+name)
        return float(channels[0][osc.numSamples-1]) if channels and osc.numSamples else default
    clock=ch('clock')
    if clock>=0 and clock!=s['clock']:
        s.update(clock=clock,heartbeat=now)
    fresh=now-s['heartbeat']<.35
    if not demo and fresh and now>s.get('poll',0):
        s['poll']=now+.65
        count=int(ch('eye_url_n'))
        if 0<count<=240:
            try:
                url=b''.join(int(ch('eye_url'+str(i))).to_bytes(3,'big') for i in range((count+2)//3))[:count].decode()
                if url.startswith('rtsp://') and r.par.Autoeye.eval():
                    if r.par.Eyeurl.eval()!=url: r.par.Eyeurl=url
                    parts=urlsplit(url)
                    params=dict(parse_qsl(parts.query))
                    if params.get('camera')=='eyes' and r.par.Autoscene.eval():
                        params['camera']='world'
                        world=urlunsplit(parts._replace(query=urlencode(params)))
                        if r.par.Sceneurl.eval()!=world: r.par.Sceneurl=world
            except (ValueError,OverflowError): pass

    lookup=s.get('lookup')
    if lookup and lookup.done():
        try:
            urls=lookup.result()
            for name,url in urls.items():
                enabled=r.par.Autoeye.eval() if name=='Eyeurl' else r.par.Autoscene.eval()
                if enabled and url.startswith('rtsp://'): getattr(r.par,name).val=url
        except (ValueError,OSError,subprocess.SubprocessError): pass
        s['lookup']=None
    missing=((r.par.Autoeye.eval() and not r.par.Eyeurl.eval()) or
             (r.par.Autoscene.eval() and not r.par.Sceneurl.eval()))
    if not demo and missing and not s.get('lookup') and now>s.get('discover',0):
        s['discover']=now+12
        s['lookup']=s['pool'].submit(camera_urls,folder,r.par.Neonhost.eval().strip())
    hands=[]
    stamp=0
    if not demo and r.par.Webcam.eval():
        tracker=s.get('tracker')
        if (tracker is None or not tracker.worker.is_alive()) and now>s.get('retry',0):
            s['retry']=now+3
            try: tracker=s['tracker']=Hands(folder/'day13-hands')
            except OSError: s['status']='Hand tracker missing. Keep day13-hands beside the project.'
        if tracker is not None and tracker.worker.is_alive():
            if now-s['scan']>.045:
                a=r.op('hand_frame').numpyArray(delayed=True)
                if a is not None and a.shape==(360,640,4):
                    tracker.submit(np.clip(a[::-1]*255,0,255).astype(np.uint8).tobytes())
                s['scan']=now
            stamp,obs=tracker.latest
            if now-stamp<.25: hands=[display_hand(h,True) for h in obs]
    handles=s['handles']
    handles.update(hands,stamp,now)
    if s['keyjob'] and s['keyjob'].done():
        key=s['keyjob'].result()
        s['keyjob']=None
        if key:
            s['key']=key
            r.par.Reader='OpenAI'
            s['status']='Key ready. Scan Page sends one Neon scene frame to OpenAI.'
    if s['mode']!=demo:
        s.update(mode=demo,page=None,registration=None,request=demo,signature=[],previous=[],pending_image=None)
        s['generation']=s.get('generation',0)+1
        s['status']='Loading demo…' if demo else 'Aim Neon at a page, then press Scan Page.'
    if s['job'] and s['job'].done():
        try:
            result=s['job'].result()
            if isinstance(result,tuple):
                result,s['pending_ref']=result
            if result is None: s['status']='Import canceled'
            elif s['jobgen']==s['generation']:
                s.update(page=result,registration=s['pending_ref'],loaded=now,align=0)
                s['signature']=s.get('pending_signature') or fingerprint(result.words)
                s['status']=f'{len(result.words)} words / {len(result.figures)} figures · '+('Demo' if demo else 'page saved')
        except Exception as err:
            s['status']='Scan failed: '+str(err)[:160]
            if r.par.Autopages.eval(): r.par.Autopages=False
        s['job']=None
    auto=bool(r.par.Autopages.eval() and not demo)
    probe=s.get('inspecting')
    if probe and probe.done():
        s['inspecting']=None
        try:
            observed=probe.result()
            sig=page_signature(s['probe_image'],observed)
            if (auto and not s['job'] and not s['request'] and bool(sig)
                    and not same_text(sig,s['signature']) and same_text(sig,s['previous'])):
                s.update(request=True,pending_image=s['probe_image'],observed=observed)
            s['previous']=sig
        except (ValueError, OSError, subprocess.SubprocessError):
            s['previous']=[]
        s['probe_image']=None
    if auto and not s['job'] and not s.get('inspecting') and not s['request'] and now>s.get('next_probe',0):
        aligned=s['registration'] and s['registration'].inverse is not None
        s['next_probe']=now+(4 if aligned else 1.2)
        frame=scene_image(r)
        if frame is not None:
            s['probe_image']=frame
            s['inspecting']=s['pool'].submit(inspect_page,folder,frame)
    if s['request'] and not s['job']:
        s['request']=False
        image=s.pop('pending_image',None)
        observed=s.pop('observed',None)
        if image is None and not demo: image=scene_image(r)
        mode='Demo' if demo else r.par.Reader.eval()
        if mode=='OpenAI' and not s['key']:
            s['status']='Press Enter API Key, then Scan Page.'
            r.par.Autopages=False
        elif not demo and image is None: s['status']='Waiting for Neon scene video. Check Scene RTSP, then scan again.'
        else:
            s['pending_ref']=None if demo else Registration(image)
            s['pending_signature']=page_signature(image,observed) if observed is not None else []
            s['jobgen']=s['generation']
            s['job']=s['pool'].submit(recognize,folder,image,mode,s['key'],observed)
            s['status']='Recognizing page…'
    # Physics uses top-left pixels; the two GPU circle centres use bottom-left units.
    eyes=np.column_stack((handles.positions[:,0]*H,(1-handles.positions[:,1])*H,handles.radii*H))
    page=s['page']
    gaze=None
    if page is not None:
        if demo:
            slot=int((now-s['loaded'])/.48)
            if page.figures and 3<=slot<9:
                box=page.figures[0].box
            else:
                i=min(len(page.words)-1,slot-(6 if page.figures and slot>=9 else 0))
                box=page.boxes[i]
            gaze=(box[:2]+box[2:])*.5
        else:
            ref=s['registration']
            if now>s['align']:
                s['align']=now+.18
                current=scene_image(r)
                if current is None: ref.inverse=None
                else: ref.align(current)
            raw=np.array([ch('raw_gx'),ch('raw_gy')])
            # The original TD-Neon launcher sends smoothed gx/gy with Y upwards.
            legacy=not (osc.chans('raw_gx') or osc.chans('/raw_gx'))
            if legacy: raw=np.array([ch('gx'),1-ch('gy')])
            valid=ch('valid')==1 if legacy else ch('worn')==1 and ch('valid')==1
            if fresh and valid and np.all((raw>=0)&(raw<=1)):
                gaze=ref.gaze(raw)
        page.look(gaze,now,eyes)
    display=s['status']
    if page is not None and not demo and display.endswith('page saved'):
        reason=('waiting for valid gaze' if not fresh or ch('valid')!=1
                else 'face the scanned page' if s['registration'].inverse is None else 'reading')
        display=f'{len(page.words)} words / {len(page.figures)} figures · {len(page.motes)} released · {reason}'
    if r.par.Status.eval()!=display: r.par.Status=display
    dt=min(.05,max(0,now-s['last']))
    s['last']=now
    s['mask']=page.draw(now,dt,eyes) if page is not None else None
    payload=np.zeros((1,3,4),np.float32)
    payload[0,:2,:2]=handles.positions
    payload[0,:2,2]=handles.radii
    payload[0,2]=bool(demo),bool(r.par.Webcam.eval() and not demo),bool(r.par.Eyeurl.eval() and not demo),0
    scriptOp.copyNumpyArray(payload)
