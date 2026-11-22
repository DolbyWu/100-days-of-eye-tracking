"""Neon acquisition, OSC controls, and timestamp-driven replay."""
import argparse
import asyncio
from bisect import bisect_right
import csv
from contextlib import ExitStack
import json
import math
from pathlib import Path
import secrets
import socket
import struct
import time


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def fields(value):
    """Keep the SDK's scalar and nested named-tuple fields in the capture."""
    if hasattr(value, "_asdict"):
        value = value._asdict()
    if isinstance(value, dict):
        return {key: fields(item) for key, item in value.items()}
    if isinstance(value, (str, bool, int)):
        return value
    return number(value)


def padded(value):
    value = value.encode("ascii") + b"\0"
    return value + b"\0" * (-len(value) % 4)


def osc_bundle(channels):
    bundle = bytearray(b"#bundle\0" + struct.pack(">Q", 1))
    for name, value in channels.items():
        message = padded("/" + name) + padded(",f") + struct.pack(">f", value)
        bundle.extend(struct.pack(">I", len(message)))
        bundle.extend(message)
    return bundle


class Controls:
    def __init__(self, args, output, writer=None):
        self.args = args
        self.output = output
        self.writer = writer
        self.session = secrets.randbelow(2**23 - 1) + 1
        self.channels = dict(gx=.5, gy=.5, vx=0, vy=0, speed=0, valid=0,
                             pupil_l=-1, pupil_r=-1, pupil_delta=0, worn=0, dwell=0,
                             aperture_l=-1, aperture_r=-1, blink=0,
                             fixation=0, saccade=0, fixation_onset=0,
                             saccade_onset=0, scene_frame=-1)
        self.last_gaze = None
        self.last_stamp = None
        self.previous = None
        self.anchor = None
        self.baseline = None
        self.origin = None

    def ingest(self, stamp, stream, data):
        if self.writer:
            self.writer.writerow((stamp, stream, json.dumps(data, allow_nan=False)))
        if self.origin is None:
            self.origin = stamp
        if stream in ("blink", "fixation", "saccade", "fixation_onset", "saccade_onset"):
            self.channels[stream] += 1
        elif stream == "imu":
            self.channels["imu_t"] = (stamp - self.origin) / 1e9
            for group in ("accel_data", "gyro_data", "quaternion"):
                for axis, value in (data.get(group) or {}).items():
                    if number(value) is not None:
                        self.channels[group + "_" + axis] = value
        elif stream == "gaze":
            self.gaze(stamp, data)

    def gaze(self, stamp, data):
        ch = self.channels
        if self.last_stamp is not None and stamp <= self.last_stamp:
            return
        self.last_gaze = time.monotonic()
        self.last_stamp = stamp
        ch["gaze_t"] = (stamp - self.origin) / 1e9
        x, y = number(data.get("x")), number(data.get("y"))
        ch["worn"] = int(number(data.get("worn")) == 1)
        valid = bool(ch["worn"] and x is not None and y is not None
                     and 0 <= x < self.args.width and 0 <= y < self.args.height)
        for target, source in (("pupil_l", "pupil_diameter_left"),
                               ("pupil_r", "pupil_diameter_right"),
                               ("aperture_l", "eyelid_aperture_left"),
                               ("aperture_r", "eyelid_aperture_right")):
            value = number(data.get(source))
            ch[target] = value if valid and value is not None and value >= 0 else -1
        ch["valid"] = int(valid)
        if not valid:
            self.previous = None
            self.anchor = None
            ch.update(vx=0, vy=0, speed=0, pupil_delta=0, dwell=0)
            return
        x, y = x / self.args.width, 1 - y / self.args.height
        dt = (stamp - self.previous) / 1e9 if self.previous is not None else 0
        self.previous = stamp
        if 0 < dt < .25:
            alpha = -math.expm1(-dt / .035)
            dx, dy = alpha * (x - ch["gx"]), alpha * (y - ch["gy"])
            beta = -math.expm1(-dt / .055)
            vx = ch["vx"] + beta * (dx / dt - ch["vx"])
            vy = ch["vy"] + beta * (dy / dt - ch["vy"])
            ch.update(gx=ch["gx"] + dx, gy=ch["gy"] + dy, vx=vx, vy=vy,
                      speed=math.hypot(vx, vy))
        else:
            ch.update(gx=x, gy=y, vx=0, vy=0, speed=0)
        # Spatial dwell estimate on raw scene UVs, independent of the event stream.
        if (not 0 < dt < .25 or self.anchor is None
                or math.hypot(x - self.anchor[0], y - self.anchor[1]) > .023):
            self.anchor = (x, y, stamp)
        ch["dwell"] = (stamp - self.anchor[2]) / 1e9
        pupils = [ch[key] for key in ("pupil_l", "pupil_r") if ch[key] > 0]
        ch["pupil_delta"] = 0
        if pupils:
            mean = sum(pupils) / len(pupils)
            if self.baseline is None:
                self.baseline = mean
            self.baseline += -math.expm1(-min(max(dt, 0), .1) / 8) * (mean - self.baseline)
            ch["pupil_delta"] = min(2, max(-2, mean - self.baseline))

    def send(self, seconds=0, source_ns=None):
        stale = (self.last_gaze is None or time.monotonic() - self.last_gaze > .3
                 if source_ns is None else
                 self.last_stamp is None or source_ns - self.last_stamp > 300_000_000)
        if stale:
            self.channels.update(valid=0, worn=0, vx=0, vy=0, speed=0, dwell=0, pupil_delta=0,
                                 pupil_l=-1, pupil_r=-1, aperture_l=-1, aperture_r=-1)
            self.previous = None
            self.anchor = None
        # IEEE float32 represents each unsigned 16-bit word exactly.
        epoch = self.origin or 0
        words = {f"epoch{i}": (epoch >> (16*i)) & 65535 for i in range(4)}
        self.output.sendto(osc_bundle(dict(self.channels, session=self.session,
                                            clock=seconds, **words)),
                           (self.args.host, self.args.port))


def table(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            yield {" ".join(key.split()): value for key, value in row.items() if key is not None}


def capture_rows(path):
    for row in table(path):
        yield int(row["timestamp_ns"]), row["stream"], json.loads(row["payload_json"])


def cloud_rows(folder):
    eyes = folder / "3d_eye_states.csv"
    eye_columns = {
        "pupil diameter left [mm]": "pupil_diameter_left",
        "pupil diameter right [mm]": "pupil_diameter_right",
        "eyelid aperture left [mm]": "eyelid_aperture_left",
        "eyelid aperture right [mm]": "eyelid_aperture_right",
    }
    eye_by_stamp = {}
    if eyes.exists():
        for row in table(eyes):
            state = {dest: number(row.get(src)) for src, dest in eye_columns.items()}
            state["source"] = row
            eye_by_stamp[int(row["timestamp [ns]"])] = state
    for row in table(folder / "gaze.csv"):
        stamp = int(row["timestamp [ns]"])
        yield stamp, "gaze", dict(eye_by_stamp.get(stamp, {}), x=number(row["gaze x [px]"]),
                                       y=number(row["gaze y [px]"]), worn=number(row["worn"]) == 1)
    for stream in ("blink", "fixation", "saccade"):
        path = folder / (stream + "s.csv")
        if path.exists():
            for row in table(path):
                yield int(row["end timestamp [ns]"]), stream, row
    path = folder / "imu.csv"
    if path.exists():
        for row in table(path):
            # Pupil Cloud columns are preserved verbatim in captures.
            yield int(row["timestamp [ns]"]), "imu", {
                "accel_data": {axis: number(row.get("acceleration " + axis + " [g]"))
                               for axis in "xyz"},
                "gyro_data": {axis: number(row.get("gyro " + axis + " [deg/s]"))
                              for axis in "xyz"},
                "quaternion": {axis: number(row.get("quaternion " + axis)) for axis in "wxyz"},
                "source": row,
            }


def replay(args, output, writer):
    source = args.source
    rows = sorted(cloud_rows(source) if source.is_dir() else capture_rows(source),
                  key=lambda item: item[0])
    timestamps = args.world_timestamps
    if timestamps is None and source.is_dir():
        timestamps = source / "world_timestamps.csv"
        if not timestamps.exists():
            timestamps = None
    frames = [int(row["timestamp [ns]"]) for row in table(timestamps)] if timestamps else []
    if any(b <= a for a, b in zip(frames, frames[1:])):
        raise ValueError("World frame timestamps must increase in MP4 frame order.")
    if not rows:
        raise ValueError("Replay has no telemetry rows.")
    start = min(rows[0][0], frames[0]) if frames else rows[0][0]
    end = max(rows[-1][0], frames[-1]) if frames else rows[-1][0]
    while True:
        controls = Controls(args, output, writer)
        controls.origin = start
        wall = time.monotonic()
        index = 0
        while True:
            now = min(end, start + int((time.monotonic() - wall) * args.rate * 1e9))
            while index < len(rows) and rows[index][0] <= now:
                controls.ingest(*rows[index])
                index += 1
            controls.channels["scene_frame"] = bisect_right(frames, now) - 1
            controls.send((now - start) / 1e9, source_ns=now)
            if now == end:
                break
            time.sleep(1 / 60)
        if not args.loop:
            return


def demo(args, output, writer):
    controls = Controls(args, output, writer)
    epoch, wall = time.time_ns(), time.monotonic()
    last_blink = 0
    while not args.duration or time.monotonic() - wall < args.duration:
        t = time.monotonic() - wall
        path_time = int(t / 8) * 8 + min(t % 8, 5.5)
        stamp = epoch + int(t * 1e9)
        controls.ingest(stamp, "gaze", {
            "x": args.width * (.5 + .30 * math.sin(path_time * 1.35)),
            "y": args.height * (.5 + .30 * math.sin(path_time * 2.1 + .5)),
            "worn": not 7.0 <= t % 8 < 8.0,
            "pupil_diameter_left": 3.5 + .45 * math.sin(t * 1.1),
            "pupil_diameter_right": 3.6 + .4 * math.sin(t * 1.1),
        })
        if int(t / 3) > last_blink:
            last_blink = int(t / 3)
            controls.ingest(stamp, "blink", {"end_time_ns": stamp})
        controls.send(t)
        time.sleep(1 / 60)


async def live_session(args, controls):
    from pupil_labs.realtime_api import (Device, Network, receive_eye_events_data,
                                        receive_gaze_data, receive_imu_data)

    if args.device:
        device = Device(args.device, args.device_port)
    else:
        async with Network() as network:
            found = await network.wait_for_new_device(timeout_seconds=8)
        if found is None:
            raise ValueError("No Neon discovered. Start Companion on the same LAN or pass --device IP.")
        device = Device.from_discovered_device(found)
    async with device:
        status = await device.get_status()
        gaze = status.direct_gaze_sensor()
        if not gaze or not gaze.connected:
            raise ValueError("Neon reports its gaze sensor disconnected.")
        for title, sensor in (("Scene RTSP", status.direct_world_sensor()),
                              ("Eye RTSP", status.direct_eyes_sensor())):
            if sensor and sensor.connected:
                print(f"{title}: {sensor.url}", flush=True)

        async def consume(sensor, receive, stream):
            async for item in receive(sensor.url, run_loop=False):
                data = fields(item)
                stamp = item.timestamp_unix_ns
                if stream == "event":
                    name = {0: "saccade", 1: "fixation", 2: "saccade_onset",
                            3: "fixation_onset", 4: "blink"}.get(item.event_type, "event")
                else:
                    name = stream
                controls.ingest(stamp, name, data)

        gaze_task = asyncio.create_task(consume(gaze, receive_gaze_data, "gaze"))
        tasks = [gaze_task]
        for sensor, receive, name in ((status.direct_eye_events_sensor(), receive_eye_events_data, "event"),
                                      (status.direct_imu_sensor(), receive_imu_data, "imu")):
            if sensor and sensor.connected:
                tasks.append(asyncio.create_task(consume(sensor, receive, name)))
            else:
                print(f"{name} stream unavailable at connection.", flush=True)
        wall = time.monotonic()
        optional_reported = set()
        try:
            while True:
                if gaze_task.done():
                    gaze_task.result()
                    raise RuntimeError("Gaze stream ended")
                if time.monotonic() - (controls.last_gaze or wall) > 4:
                    raise TimeoutError("No gaze samples received for four seconds")
                for task in tasks[1:]:
                    if task.done() and task not in optional_reported:
                        print(f"Optional stream ended: {task.exception()}", flush=True)
                        optional_reported.add(task)
                controls.send(time.monotonic() - wall)
                await asyncio.sleep(1 / 60)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def live(args, output, writer):
    # Import once outside retry so a missing dependency fails immediately.
    import pupil_labs.realtime_api  # noqa: F401

    while True:
        controls = Controls(args, output, writer)
        try:
            await live_session(args, controls)
        except Exception as exc:
            print(f"Neon disconnected: {exc}. Retrying in 2 s.", flush=True)
            # Keep the current source identity while marking its gaze invalid.
            controls.last_gaze = None
            controls.send()
            await asyncio.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9012)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--record", type=Path, help="Create a new telemetry CSV.")
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("demo").add_argument("--duration", type=float, default=0)
    live_args = modes.add_parser("live")
    live_args.add_argument("--device", help="Neon Companion IP or hostname")
    live_args.add_argument("--device-port", type=int, default=8080)
    replay_args = modes.add_parser("replay")
    replay_args.add_argument("source", type=Path, help="Bridge CSV or one Pupil Cloud export folder")
    replay_args.add_argument("--world-timestamps", type=Path)
    replay_args.add_argument("--rate", type=float, default=1)
    replay_args.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    if min(args.width, args.height) <= 0 or not 1 <= args.port <= 65535:
        parser.error("Dimensions and UDP port must be positive and in range.")
    if args.mode == "replay" and (not math.isfinite(args.rate) or args.rate <= 0):
        parser.error("Replay rate must be positive and finite.")
    if args.mode == "demo" and (not math.isfinite(args.duration) or args.duration < 0):
        parser.error("Demo duration must be finite and nonnegative.")
    try:
        with ExitStack() as stack:
            output = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
            writer = None
            if args.record:
                handle = stack.enter_context(args.record.open("x", newline="", encoding="utf-8", buffering=1))
                writer = csv.writer(handle)
                writer.writerow(("timestamp_ns", "stream", "payload_json"))
            if args.mode == "live":
                asyncio.run(live(args, output, writer))
            elif args.mode == "replay":
                replay(args, output, writer)
            else:
                demo(args, output, writer)
    except KeyboardInterrupt:
        pass
    except (ImportError, OSError, KeyError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
