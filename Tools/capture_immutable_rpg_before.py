"""One-time immutable v2.16 evidence capture; not an after approval tool."""
import gzip,hashlib,io,json,pathlib,sys
import numpy as np
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(root/'Source'))
from peer_culling_contract import read_visual,summarize
expected='f52f44353420638bb500afd37f04b9c55d7f30ab4da4c369ad4b4c98080e3c46'
def sha(raw):return hashlib.sha256(raw).hexdigest()
raw=(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes()
assert sha(raw)==expected
batches=read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
assert manifest['version']=='2.16.0' and len(batches)==1106
rows=[];uv_arrays={};sign_keys=[]
for i,b in enumerate(batches):
 r=summarize(b);r['arraySha256']={a:sha(np.asarray(b[a],dtype=t).tobytes()) for a,t in [('vertices','<f4'),('uv','<f4'),('colors','u1'),('faces','<u4')]};rows.append(r)
 if b['material'] in ('Food_Sign','Night_Print'):
  sign_keys.append([b['group'],b['material']]);uv_arrays[str(i)+'_uv']=b['uv']
paths=[]
for folder in ('Assets/TreeTopYokocho/Textures','Assets/TreeTopYokocho/Shaders','Assets/TreeTopYokocho/Editor'):
 paths += [p for p in (root/folder).rglob('*') if p.is_file() and p.suffix!='.meta']
for rel in ['Assets/TreeTopYokocho/Data/FantasyMaterials.json','Source/build_world.py','Source/shop_personality.py','Source/food_venues.py','Source/nightlife_venues.py','Source/render_preview.py','Source/fantasy_preview.py','Source/fantasy_materials.py','Source/shop_personality_legacy_materials.json']:
 paths.append(root/rel)
# Original historical oracle/inverse assets are immutable throughout this pass.
paths += [p for p in (root/'Source/testdata').glob('*') if p.is_file() and ('oracle' in p.name or 'inverse' in p.name or p.name.startswith(('shop_personality_','shop_profile_','city_roof_caps_','visual_optimization_')))]
result=dict(schema=1,version='2.16.0',nativeSha256=expected,glbSha256=sha((root/'Source/TreeTopYokocho.glb').read_bytes()),collisionSha256=sha((root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes()),rows=rows,manifest=manifest,signKeys=sign_keys,dependencies={str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(set(paths))})
out.mkdir(parents=True,exist_ok=True)
payload=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
(out/'rpg_identity_before_2_16.json.gz').write_bytes(gzip.compress(payload,mtime=0))
np.savez_compressed(out/'rpg_identity_inverse_2_17.npz',**uv_arrays)
(out/'rpg_identity_legacy_builder_2_16.cs').write_bytes((root/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_bytes())
print(json.dumps({p.name:sha(p.read_bytes()) for p in out.iterdir()},indent=2))
