"""Query the existing Neon Python environment for the advertised camera URLs."""
import asyncio
import json
import sys
from pupil_labs.realtime_api import Device, Network


async def cameras(host):
    if host:
        name, _, port=host.partition(':')
        device=Device(name,int(port or 8080))
    else:
        async with Network() as network:
            found=await network.wait_for_new_device(timeout_seconds=4)
        if found is None: return {}
        device=Device.from_discovered_device(found)
    async with device:
        status=await device.get_status()
        sensors={'Eyeurl':status.direct_eyes_sensor(),'Sceneurl':status.direct_world_sensor()}
        return {key:str(sensor.url) for key,sensor in sensors.items() if sensor and sensor.connected}

if __name__=='__main__':
    print(json.dumps(asyncio.run(cameras(sys.argv[1]))))
