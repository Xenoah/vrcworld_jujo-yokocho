"""Capture immutable accepted v2.18 evidence only; never approve v2.19 art."""
import gzip,hashlib,json,pathlib,sys
from pygltflib import GLTF2
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(root/'Source'))
from rpg_identity_contract import summarize_batches
from peer_culling_contract import read_visual
from audit_shop_personality_glb import access,semantic_material,identity_scene_errors,image_fingerprints
NATIVE='d0386d484fc9de77ee43d41db4a36aab916027bc81091ad573afca13a0fc69db'
GLB='f0c2313043ec2fdaeda99a80d516ef592a01b5b5cdfc35d34c02c5eb3bafc32f'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def write(name,v):
 raw=gzip.compress(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(),mtime=0);(out/name).write_bytes(raw);print(name,sha(raw),len(raw))
data=root/'Assets/TreeTopYokocho/Data';assert sha((data/'VisualMeshes.bytes').read_bytes())==NATIVE
m=json.loads((data/'WorldManifest.json').read_text());assert m['version']=='2.18.0'
rows=summarize_batches(read_visual(data/'VisualMeshes.bytes'));assert len(rows)==1107
# Full before metadata is needed by test-only exact inversion; production
# after admission uses compact per-field hashes and exact added row records.
write('projecting_sign_before_2_18.json.gz',dict(schema=1,version='2.18.0',nativeSha256=NATIVE,glbSha256=GLB,collisionSha256=sha((data/'CollisionMeshes.bytes').read_bytes()),rows=rows,manifest=m,manifestFieldHashes={k:digest(v) for k,v in m.items()}))
path=root/'Source/TreeTopYokocho.glb';assert sha(path.read_bytes())==GLB
g=GLTF2().load(str(path));assert not identity_scene_errors(g,'accepted v2.18')
def record(i):
 if i is None:return None
 a=g.accessors[i]
 return dict(componentType=a.componentType,normalized=a.normalized,type=a.type,count=a.count,sha256=sha(access(g,i).tobytes()),minimum=a.min,maximum=a.max,sparse=None if a.sparse is None else json.loads(a.sparse.to_json()),extensions=a.extensions,extras=a.extras)
meshes=[]
for mesh in g.meshes:
 p=mesh.primitives[0]
 meshes.append(dict(name=mesh.name,material=g.materials[p.material].name,attributes={k:record(v) for k,v in vars(p.attributes).items()},indices=record(p.indices)))
def view_record(v):
 value=json.loads(v.to_json());offset=value.pop('byteOffset',None) or 0;value['sha256']=sha(g.binary_blob()[offset:offset+v.byteLength]);return value
def image_record(im):
 value=json.loads(im.to_json());index=value.pop('bufferView');v=g.bufferViews[index];value['sha256']=sha(g.binary_blob()[(v.byteOffset or 0):(v.byteOffset or 0)+v.byteLength]);return value
raw=json.loads(g.to_json());header={k:v for k,v in raw.items() if k not in ('accessors','bufferViews','buffers','images','materials','meshes','nodes','samplers','scenes','textures')}
scene=json.loads(g.scenes[0].to_json());scene.pop('nodes',None)
write('projecting_sign_glb_before_2_18.json.gz',dict(schema=1,version='2.18.0',glbSha256=GLB,meshes=meshes,materials={m.name:semantic_material(g,m) for m in g.materials},materialOrder=[m.name for m in g.materials],images=image_fingerprints(g),textures=[json.loads(t.to_json()) for t in g.textures],samplers=[json.loads(s.to_json()) for s in g.samplers],header=header,scene=scene,accessorCount=len(g.accessors),bufferViewCount=len(g.bufferViews),allAccessors=[record(i) for i in range(len(g.accessors))],allBufferViews=[view_record(v) for v in g.bufferViews],imageDescriptors=[image_record(im) for im in g.images]))
