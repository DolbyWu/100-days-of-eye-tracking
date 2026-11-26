import hashlib
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MeshChecks(unittest.TestCase):
    def test_meshes_match_manifest(self):
        manifest=json.loads((ROOT/'assets/manifest.json').read_text())
        for name,data in manifest['objects'].items():
            file=ROOT/'assets/meshes'/(name+'.obj')
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),data['sha256'],name)
            self.assertGreater(data['triangles'],0)
        for part in ['eye','brain','LGN','SC','V1','FEF']:
            left,right=[manifest['objects'][part+'_'+s]['center'] for s in 'LR']
            self.assertGreater(left[0],0)
            self.assertLess(right[0],0)
