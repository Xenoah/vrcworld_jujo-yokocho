"""Capture compact exact v2.16 GLB semantics, not geometry or art approval."""
import gzip,hashlib,json,pathlib,sys
from pygltflib import GLTF2
root=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(root/'Source'))
from audit_shop_personality_glb import access,semantic_material,identity_scene_errors,image_fingerprints
expected='65fdc1ce1da77db04ceae244ae2089852756705dd89f60e735b177336b6a0b15'
def sha(raw):return hashlib.sha256(raw).hexdigest()
path=root/'Source/TreeTopYokocho.glb';assert sha(path.read_bytes())==expected
g=GLTF2().load(str(path));assert not identity_scene_errors(g,'baseline');rows=[]
def record(index):
 if index is None:return None
 a=g.accessors[index];return dict(componentType=a.componentType,normalized=a.normalized,type=a.type,count=a.count,sha256=sha(access(g,index).tobytes()),minimum=a.min,maximum=a.max,sparse=None if a.sparse is None else json.loads(a.sparse.to_json()),extensions=a.extensions,extras=a.extras)
for mesh in g.meshes:
 p=mesh.primitives[0]
 rows.append(dict(name=mesh.name,material=g.materials[p.material].name,attributes={k:record(v) for k,v in vars(p.attributes).items()},indices=record(p.indices)))
result=dict(schema=1,version='2.16.0',glbSha256=expected,meshes=rows,materials={m.name:semantic_material(g,m) for m in g.materials},images=image_fingerprints(g))
out.write_bytes(gzip.compress(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(),mtime=0));print(sha(out.read_bytes()),len(result['meshes']),len(result['materials']))
