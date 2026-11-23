import argparse
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from make_surface_markers import generate
from surface_mapping import SurfaceMapper
from eye_tracking import EyeTracker
import neon_bridge


@unittest.skipUnless(cv2 is not None, "Install requirements-mapping.txt")
class TestSurface(unittest.TestCase):
    def setUp(self):
        self.image,self.layout=generate()
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test-layout.json'
        import json
        self.path.write_text(json.dumps(self.layout))
        self.mapper=SurfaceMapper(self.path)
        alpha=self.image[:,:,3]>0
        self.bgr=np.full(self.image.shape[:2]+(3,),20,np.uint8)
        self.bgr[alpha]=self.image[:,:,:3][alpha]

    def test_homography_three_tags_and_loss(self):
        self.assertTrue(self.mapper.update(self.bgr))
        x,y=self.mapper.map_xy(600,400)
        self.assertLess(math.hypot(x-600,y-400),1)
        one=self.bgr.copy();one[0:140,0:140]=20
        self.assertTrue(self.mapper.update(one));self.assertEqual(self.mapper.marker_count,3)
        two=one.copy();two[0:140,-140:]=20
        self.assertFalse(self.mapper.update(two));self.assertIsNone(self.mapper.map_xy(600,400))

    def test_stale_map_is_invalid(self):
        self.mapper.update(self.bgr,now=10)
        self.assertIsNotNone(self.mapper.map_xy(600,400,now=10.1))
        self.assertIsNone(self.mapper.map_xy(600,400,now=10.4))

    def test_bridge_requires_mapped_surface(self):
        class Output:
            def sendto(self,*a): pass
        args=argparse.Namespace(width=1600,height=1200,host='127.0.0.1',port=9012)
        controls=neon_bridge.Controls(args,Output())
        controls.surface_mapper=self.mapper
        controls.ingest(1000000000,'gaze',{'x':800,'y':600,'worn':True})
        self.assertEqual(controls.channels['valid'],0)
        self.mapper.update(self.bgr)
        controls.ingest(1020000000,'gaze',{'x':600,'y':400,'worn':True})
        self.assertEqual(controls.channels['valid'],1)
        self.assertEqual(controls.channels['surface_on'],1)
        self.assertAlmostEqual(controls.channels['gx'],.5,places=2)

    def test_eye_candidates_and_blank(self):
        im=np.full((192,384,3),140,np.uint8)
        cv2.circle(im,(116,58),22,(8,8,8),-1)
        cv2.circle(im,(244,65),17,(8,8,8),-1)
        t=EyeTracker();v=t.update(im)
        self.assertEqual((v['eye_l_valid'],v['eye_r_valid']),(1,1))
        self.assertLess(abs(v['eye_l_x']*384-116),10)
        self.assertLess(abs(v['eye_r_x']*384-244),10)
        blank=np.full_like(im,140)
        self.assertEqual(EyeTracker().update(blank)['eye_l_valid'],0)


if __name__=='__main__':unittest.main()
