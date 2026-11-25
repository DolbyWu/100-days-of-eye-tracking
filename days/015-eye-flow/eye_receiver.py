from threading import Thread
from time import monotonic
from pathlib import Path
import plistlib
from urllib.parse import urlsplit, urlunsplit
import subprocess
import numpy as np

process=None
address=None
latest=None
retry=0
last_frame=0

preferences=Path.home()/'Library/Preferences/art.gazefluid.neonbridge.plist'
next_settings_check=0
previous_device=None

def sync_device(url):
    global next_settings_check,previous_device
    now=monotonic()
    if now<next_settings_check:
        return url
    next_settings_check=now+2
    try:
        with preferences.open('rb') as file:
            device=plistlib.load(file).get('device','').strip()
        if device and device!=previous_device:
            parts=urlsplit(url or 'rtsp://localhost:8086/?camera=eyes')
            host=f'[{device}]' if ':' in device else device
            url=urlunsplit((parts.scheme,f'{host}:{parts.port or 8086}',parts.path,parts.query,parts.fragment))
            parent().par.Eyeurl=url
        previous_device=device
    except (OSError,ValueError,plistlib.InvalidFileException):
        pass
    return url

def receive(child):
    global latest,last_frame
    try:
        while True:
            frame=child.stdout.read(384*192)
            if len(frame)!=384*192:return
            if child is process:
                latest=np.frombuffer(frame,np.uint8).reshape(192,384)
                last_frame=monotonic()
    finally:
        child.stdout.close()
        child.wait()

def onCook(scriptOp):
    global process,address,latest,retry,last_frame
    _=absTime.frame
    url=sync_device(parent().par.Eyeurl.eval())
    if address!=url:
        if process and process.poll() is None:process.terminate()
        address,latest,process,retry=url,None,None,0
    if process and process.poll() is None and monotonic()-last_frame>8:
        process.terminate()
        latest=None
    if url and (process is None or process.poll() is not None) and monotonic()>retry:
        last_frame=monotonic()
        retry=last_frame+3
        process=subprocess.Popen(['/opt/homebrew/bin/ffmpeg','-nostdin','-loglevel','error','-rtsp_transport','udp','-timeout','4000000','-fflags','nobuffer','-analyzeduration','500000','-probesize','200000','-i',url,'-map','0:v:0','-vf','scale=384:192','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','gray','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        Thread(target=receive,args=(process,),daemon=True).start()
    frame=latest
    if frame is None:frame=np.zeros((192,384),np.uint8)
    rgba=np.empty((192,384,4),np.uint8)
    rgba[:,:,:3]=frame[::-1,:,None]
    rgba[:,:,3]=255
    scriptOp.copyNumpyArray(rgba)
