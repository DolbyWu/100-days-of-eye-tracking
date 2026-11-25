handles = EyeHandles()
tracker = None
last_scan = -100.
retry = 0.

def onCook(scriptOp):
    global tracker, last_scan, retry
    _ = absTime.frame
    now = monotonic()
    stamp, hands = 0., []
    if (tracker is None or not tracker.worker.is_alive()) and now >= retry:
        retry = now + 3
        tracker = Hands(Path(project.folder).parent/'014-reading-orbits'/'day13-hands')
    if tracker is not None and tracker.worker.is_alive():
        if now-last_scan > .045:
            frame = scriptOp.inputs[0].numpyArray(delayed=True)
            if frame is not None and frame.shape == (360,640,4):
                tracker.submit(np.clip(frame[::-1]*255,0,255).astype(np.uint8).tobytes())
            last_scan = now
        stamp, observations = tracker.latest
        if now-stamp < .25:
            hands = [display_hand(hand, True) for hand in observations]
    handles.update(hands, stamp, now)
    payload = np.zeros((1,3,4),np.float32)
    payload[0,:2,:2] = handles.positions
    payload[0,:2,2] = handles.radii
    payload[0,2] = (0,1,1,0)
    scriptOp.copyNumpyArray(payload)
