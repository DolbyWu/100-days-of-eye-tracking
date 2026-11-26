import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from signals import Signals,demo

class SignalTests(unittest.TestCase):
    def setUp(self):
        self.s=Signals(json.loads((ROOT/'config/activation.json').read_text()))
    def sample(self,t,x=.4,**kw):
        p=dict(session=1,gaze_t=t,valid=1,gx=x,gy=.5,blink=0,pupil_l=None,pupil_r=None)
        p.update(kw)
        return self.s.step(p,t)
    def test_classes_and_decay(self):
        for i in range(12):self.sample(i*.02)
        self.assertEqual(self.s.event,'fixation')
        self.sample(.24,.85)
        self.assertEqual(self.s.event,'saccade')
        self.assertGreater(self.s.level['FEF'],0)
        for i in range(1,120):self.sample(.24+i*.04,valid=0)
        self.assertLess(max(self.s.level.values()),.001)
        self.assertNotIn('brainstem',self.s.level)
    def test_timestamp_session(self):
        self.sample(0)
        self.sample(.03)
        self.s.step(dict(session=1,valid=1,gaze_t=.03,gx=.4,gy=.5),1)
        self.assertEqual(self.s.direction,(0,0))
        self.sample(1.1,session=2,blink=99)
        self.assertEqual(self.s.event,'')
        self.assertEqual(self.s.flash_until,-float('inf'))
    def test_native_blink_missing_and_baseline(self):
        self.sample(0,blink=2,pupil_l=4)
        self.sample(.02,blink=3,pupil_l=9)
        self.assertEqual(self.s.baseline,4)
        self.assertGreater(self.s.level['brainstem'],0)
        self.sample(.23,blink=3)
        self.assertEqual(self.s.pupil,0)
    def test_demo(self):
        events=set()
        for i in range(600):
            t=i/60
            vals=self.s.step(demo(t),t)
            self.assertTrue(all(0<=v<=1 for v in vals.values()))
            events.add(self.s.event)
        self.assertTrue({'saccade','fixation','smooth_motion'}<=events)
if __name__=='__main__':unittest.main()
