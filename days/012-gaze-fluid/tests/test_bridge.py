import argparse
from pathlib import Path
from struct import unpack
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import neon_bridge as bridge


class Receiver:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, address):
        assert address == ("127.0.0.1", 9012)
        assert packet[:16] == b"#bundle\0" + b"\0"*7 + b"\1"
        values = {}
        offset = 16
        while offset < len(packet):
            length, = unpack(">I", packet[offset:offset+4])
            msg = packet[offset+4:offset+4+length]
            values[msg.split(b"\0", 1)[0][1:].decode()] = unpack(">f", msg[-4:])[0]
            offset += 4 + length
        self.frames.append(values)


class Signals(unittest.TestCase):
    epoch = 1_770_000_000_000_000_123

    def setUp(self):
        self.receiver = Receiver()
        self.args = argparse.Namespace(width=1600, height=1200, host="127.0.0.1", port=9012)
        self.control = bridge.Controls(self.args, self.receiver)

    def ingest(self, ns=0, x=400, y=300, worn=True, **eyes):
        self.control.ingest(self.epoch + ns, "gaze", dict(x=x, y=y, worn=worn, **eyes))
        return self.control.channels

    def test_scene_normalization(self):
        channels = self.ingest()
        self.assertEqual((channels["gx"], channels["gy"], channels["valid"]), (.25, .75, 1))
        self.assertEqual(self.ingest(1, x=1600)["valid"], 0)
        self.assertEqual(self.ingest(2, y=float("nan"))["valid"], 0)
        self.assertEqual(self.ingest(3, worn="0")["valid"], 0)

    def test_missing_eye_data_and_pupil_baseline(self):
        ch = self.ingest()
        self.assertEqual((ch["pupil_l"], ch["pupil_r"], ch["pupil_delta"]), (-1,-1,0))
        ch = self.ingest(20_000_000, pupil_diameter_right=4)
        self.assertEqual(ch["pupil_delta"], 0)
        ch = self.ingest(40_000_000, pupil_diameter_right=5, pupil_diameter_left=float("nan"))
        self.assertGreater(ch["pupil_delta"], .9)
        self.assertEqual(ch["pupil_l"], -1)

    def test_dwell_velocity_and_reset(self):
        self.ingest()
        ch = self.ingest(125_000_000, x=402)
        self.assertEqual(ch["dwell"], .125)
        ch = self.ingest(140_000_000, x=600)
        self.assertGreater(ch["vx"], 0)
        self.assertEqual(ch["dwell"], 0)
        self.assertEqual(self.ingest(150_000_000, worn=False)["speed"], 0)
        self.assertEqual(self.ingest(160_000_000, x=900)["speed"], 0)

    def test_integer_timestamp_order_and_stale_gate(self):
        self.ingest()
        ch = self.ingest(5_000_000)
        self.ingest(4_000_000, worn=False)
        self.assertEqual((ch["gaze_t"], ch["valid"]), (.005, 1))
        self.control.send(.4, self.epoch + 400_000_000)
        values = self.receiver.frames[-1]
        self.assertEqual(values["valid"], 0)
        self.assertEqual(sum(int(values[f"epoch{i}"]) << (16*i) for i in range(4)), self.epoch)

    def test_cloud_join_frame_alignment_and_event_count(self):
        t = self.epoch
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "gaze.csv").write_text(f"timestamp [ns],gaze x [px],gaze y [px],worn\n{t},400,300,1\n")
            (folder / "3d_eye_states.csv").write_text(f"timestamp [ns],pupil diameter left [mm]\n{t},4\n")
            (folder / "blinks.csv").write_text(f"end timestamp [ns]\n{t+31_000_000}\n")
            (folder / "world_timestamps.csv").write_text(f"timestamp [ns]\n{t-1}\n{t+29_000_000}\n{t+61_000_000}\n")
            self.args.source, self.args.world_timestamps = folder, None
            self.args.rate, self.args.loop = 1, False
            clock = [0.]
            with patch.object(bridge.time, "monotonic", lambda: clock[0]), patch.object(
                bridge.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration)
            ):
                bridge.replay(self.args, self.receiver, None)
        frames = self.receiver.frames
        self.assertEqual(frames[0]["scene_frame"], 0)
        self.assertEqual(frames[0]["valid"], 0)
        self.assertTrue(any(f["pupil_l"] == 4 and f["scene_frame"] == 1 for f in frames))
        self.assertEqual((frames[-1]["scene_frame"], frames[-1]["blink"]), (2,1))


if __name__ == "__main__":
    unittest.main()
