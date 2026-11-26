"""Run with blender -b --factory-startup --disable-autoexec --python scripts/prepare_assets.py."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'assets'
RAW = ASSETS/'raw'
RAW.mkdir(exist_ok=True)
DEST = ASSETS/'meshes'
DEST.mkdir(exist_ok=True)
REV = '7be0bfc49409b45fda74bf86fc13086fad0f4df2'
URL = f'https://raw.githubusercontent.com/Z-Anatomy/Models-of-human-anatomy/{REV}/Z-Anatomy.zip'
SHA = 'e029688545627bd0214b269e1063143abb580aad72b2c2445d6d8a9a0d9da736'
archive = RAW/'Z-Anatomy.zip'
if not archive.exists():
    urllib.request.urlretrieve(URL, archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == SHA
blend = RAW/'Startup.blend'
with zipfile.ZipFile(archive) as z:
    blend.write_bytes(z.read('Z-Anatomy/Startup.blend'))
bpy.ops.wm.open_mainfile(filepath=str(blend),use_scripts=False)
objs = {o.name:o for o in bpy.data.objects if o.type=='MESH'}
def collections(o):
    return {c.name for c in o.users_collection}

groups = {}
bones = ['Frontal bone','Occipital bone','Ethmoid bone','Sphenoid bone','Mandible','Vomer']
paired = ['Parietal bone','Temporal bone','Maxilla','Zygomatic bone','Nasal bone','Lacrimal bone','Palatine bone','Inferior nasal concha']
groups['skull'] = [n for n in bones+[k+'.'+s for k in paired for s in 'lr'] if n in objs]
groups['skull'] += [n for n,o in objs.items() if 'Teeth' in collections(o) and n.endswith(('.l','.r'))]
for side in 'lr':
    suffix='.'+side
    groups['brain_'+side.upper()] = [n for n,o in objs.items() if n.endswith(suffix) and 'Neo-cortex' in collections(o)]
    for key,part in [('eye','Sclera'),('iris','Iris'),('LGN','Lateral geniculate body'),('SC','Superior colliculus'),('tract','Optic tract'),('V1','Calcarine sulcus'),('FEF','Middle frontal gyrus'),('IPS','Intraparietal sulcus'),('MT_MST','Middle temporal gyrus')]:
        groups[key+'_'+side.upper()] = [part+suffix]
groups['chiasm']=['Optic chiasm.l','Optic chiasm.r']
groups['brainstem']=[n+'.'+s for n in ('Midbrain','Pons','Medulla oblongata') for s in 'lr']
groups['cerebellum']=[n for n,o in objs.items() if 'Cerebellum' in collections(o) and not n.endswith('.j')]
def vertices(o):
    coords=np.empty(len(o.data.vertices)*3,np.float32)
    o.data.vertices.foreach_get('co',coords)
    matrix=np.array(o.matrix_world)
    return np.einsum('ij,nj->ni',matrix[:3,:3],coords.reshape(-1,3))+matrix[:3,3]
skull=np.concatenate([vertices(objs[n]) for n in groups['skull']])
origin=(skull.max(0)+skull.min(0))/2
scale=2/np.ptp(skull,axis=0).max()
manifest=dict(source=URL,revision=REV,sha256=SHA,original_blend_sha256=hashlib.sha256(blend.read_bytes()).hexdigest(),license='CC BY-SA 4.0; upstream credits and exceptions in License.txt',transform=dict(origin=origin.tolist(),scale=scale,axes='(x,z,-y) after centering, right-handed; common skull height ~2'),objects={})
for key,names in groups.items():
    assert names,key
    vs=[]
    faces=[]
    base=0
    for name in sorted(names):
        o=objs[name]
        xyz=(vertices(o)-origin)*scale
        xyz=xyz[:,[0,2,1]]
        xyz[:,2]*=-1
        mesh=o.data
        mesh.calc_loop_triangles()
        indices=np.empty(len(mesh.loop_triangles)*3,np.int32)
        mesh.loop_triangles.foreach_get('vertices',indices)
        faces.append(indices.reshape(-1,3)+base+1)
        base+=len(xyz)
        vs.append(xyz)
    v=np.concatenate(vs)
    assert np.isfinite(v).all(),key
    file=DEST/(key+'.obj')
    with file.open('w') as f:
        f.write('o '+key+'\n')
        np.savetxt(f,v,'v %.7f %.7f %.7f')
        np.savetxt(f,np.concatenate(faces),'f %d %d %d')
    manifest['objects'][key]=dict(objects=sorted(names),triangles=sum(map(len,faces)),center=((v.min(0)+v.max(0))/2).tolist(),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),status='approximate anatomical proxy' if key.split('_')[0] in ('V1','FEF','MT') else 'named source anatomy')
manifest['unavailable']=['SEF','LC','pretectal/EW','optic nerve (no verified paired mesh selected)']
(ASSETS/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
