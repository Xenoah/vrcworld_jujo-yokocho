"""Exact GLB preservation outside the two S05 keys, plus moved-cap normals."""
from collections import Counter
import gzip,io,json
from pathlib import Path
import numpy as np
import s05_pendant_contract as c
BEFORE_NAME='s05_pendant_glb_before_2_17.json.gz'
BEFORE_SHA256='b734bb440018ff157b0d1c92df5a3dc2f49d7418778085e9958bd9964f9daf84'
PALE_NAME='s05_pendant_glb_pale_before_2_17.npz'
PALE_SHA256='a8ca4dc37ea57a0fbd58af9aceaffec57af2bcb3bd5b70d119675a4e35dc28d9'

def fixture(name,expected):
    raw=(Path(__file__).resolve().parent/'testdata'/name).read_bytes()
    if c.sha(raw)!=expected:raise ValueError('Immutable S05 GLB evidence changed: '+name)
    return raw

def triangle_records(arrays,faces,attributes):
    # Canonical cyclic rotation preserves normal/UV/color byte payloads,
    # winding and triangle multiplicity, without relying on table offsets.
    vertices=np.concatenate([np.ascontiguousarray(arrays[k]).view('u1').reshape(len(arrays[k]),-1) for k in attributes],axis=1)
    tris=vertices[faces];return Counter(min(tri.tobytes(),np.roll(tri,-1,axis=0).tobytes(),np.roll(tri,-2,axis=0).tobytes()) for tri in tris)

def audit(root,manifest=None,*,strict=False):
    from pygltflib import GLTF2
    from audit_shop_personality_glb import access,semantic_material,identity_scene_errors,image_fingerprints
    from peer_culling_contract import read_visual
    from s05_pendant_geometry_scope import local_points
    root=Path(root)
    if manifest is None:manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    errors=c.validate_gate(manifest)
    if errors:return dict(status='FAIL',errors=errors)
    prior=json.loads(gzip.decompress(fixture(BEFORE_NAME,BEFORE_SHA256)));path=root/'Source/TreeTopYokocho.glb';g=GLTF2().load(str(path))
    errors.extend(identity_scene_errors(g,'current S05'));oldname='__'.join(c.OLD_KEY);newname='__'.join(c.NEW_KEY)
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    def record(index):
        if index is None:return None
        a=g.accessors[index]
        return dict(componentType=a.componentType,normalized=a.normalized,type=a.type,count=a.count,sha256=c.sha(access(g,index).tobytes()),minimum=a.min,maximum=a.max,sparse=None if a.sparse is None else json.loads(a.sparse.to_json()),extensions=a.extensions,extras=a.extras)
    current={m.name:m for m in g.meshes};old={m['name']:m for m in prior['meshes']}
    check(len(g.meshes)==len(current)==len(old)+1 and set(current)==set(old)|{newname},'GLB exact +1 mesh roster changed')
    check([m.name for m in g.meshes if m.name!=newname]==[m['name'] for m in prior['meshes']],'GLB existing mesh order changed')
    for name,pin in old.items():
        if name==oldname:continue
        mesh=current.get(name)
        if mesh is None or len(mesh.primitives)!=1:continue
        p=mesh.primitives[0]
        check(g.materials[p.material].name==pin['material'],'Unrelated GLB material binding changed',mesh=name)
        check({k:record(v) for k,v in vars(p.attributes).items()}==pin['attributes'] and record(p.indices)==pin['indices'],'Unrelated GLB arrays/accessor bounds changed',mesh=name)
    materials={m.name:semantic_material(g,m) for m in g.materials}
    check(materials==prior['materials'],'Original GLB material/texture semantics changed')
    check(image_fingerprints(g)==prior['images'],'Original embedded image bytes/order changed')
    native={c.key(b):b for b in read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')};material_specs={m['name']:m for m in manifest['materials']};affected={}
    for key in (c.OLD_KEY,c.NEW_KEY):
        name='__'.join(key)
        if name not in current:continue
        p=current[name].primitives[0];b=native[key];arrays={k:access(g,v) for k,v in vars(p.attributes).items() if v is not None};faces=access(g,p.indices).reshape(-1,3)
        check(g.materials[p.material].name==key[1],'Affected GLB binding differs from exact key',mesh=name)
        check(set(arrays)=={'POSITION','NORMAL','TEXCOORD_0','COLOR_0'},'Affected GLB attribute roster changed',mesh=name)
        expected=b['vertices'][:,[0,2,1]].copy();expected[:,2]*=-1
        check(np.array_equal(arrays['POSITION'],expected) and np.array_equal(faces,b['faces']),'Affected GLB geometry/index differs from actual native',mesh=name)
        check(np.array_equal(arrays['COLOR_0'],b['colors']),'Affected GLB Color32 differs from actual native',mesh=name)
        # Exporter multiplies source float64 UV before float32 packing. Native
        # is already float32, so only this independent mapping diagnostic uses
        # 2e-6 arithmetic tolerance; strict approval still pins the whole GLB.
        expected_uv=b['uv']*material_specs[key[1]].get('uvScale',1);expected_uv[:,1]=1-expected_uv[:,1] # glTF texture V convention
        check(np.allclose(arrays['TEXCOORD_0'],expected_uv,rtol=0,atol=2e-6),'Affected GLB UV does not follow unchanged material scale',mesh=name)
        position=g.accessors[p.attributes.POSITION]
        check(position.min==arrays['POSITION'].min(0).tolist() and position.max==arrays['POSITION'].max(0).tolist(),'Affected GLB bounds do not match actual positions',mesh=name)
        affected[key]=(arrays,faces)
    if len(affected)==2:
        with np.load(io.BytesIO(fixture(PALE_NAME,PALE_SHA256)),allow_pickle=False) as data:oldarrays={k:data[k].copy() for k in data.files if k!='indices'};oldfaces=data['indices'].reshape(-1,3).copy()
        source=oldarrays['POSITION'][:,[0,2,1]].copy();source[:,1]*=-1
        local=local_points(source,manifest)[oldfaces];caps=np.zeros(len(oldfaces),bool)
        for x in (-1.77,1.77):
            for z in (2.24,2.45):caps|=np.all(np.abs(local-[x,.4,z])<=np.array([.75,.51,.025])/2+2e-5,axis=(1,2))
        a,f=affected[c.OLD_KEY]
        check(triangle_records(a,f,('POSITION','NORMAL','TEXCOORD_0','COLOR_0'))==triangle_records(oldarrays,oldfaces[~caps],('POSITION','NORMAL','TEXCOORD_0','COLOR_0')),'Retained pale GLB normal/UV/color/winding payload changed')
        a,f=affected[c.NEW_KEY];needed=triangle_records(oldarrays,oldfaces[caps],('POSITION',));newcaps=np.zeros(len(f),bool)
        # Stile end faces sit inside cap envelopes. Select moved caps by exact
        # immutable triangle positions, not by a broad spatial box.
        for i in range(len(f)):
            record=next(iter(triangle_records(a,f[i:i+1],('POSITION',))))
            if needed[record]:newcaps[i]=True;needed[record]-=1
        check(int(newcaps.sum())==176 and triangle_records(a,f[newcaps],('POSITION','NORMAL','COLOR_0'))==triangle_records(oldarrays,oldfaces[caps],('POSITION','NORMAL','COLOR_0')),'Moved cap GLB positions/normals/colors/winding changed')
        n=a['NORMAL'][f[~newcaps]];t=a['POSITION'][f[~newcaps]];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);cross/=np.linalg.norm(cross,axis=1)[:,None]
        check(np.allclose(n,cross[:,None,:],rtol=0,atol=1e-5),'New stile GLB normals must be flat outward face normals')
    actual=c.sha(path.read_bytes())
    if strict:check(actual==c.load_oracle(root)['glbSha256'],'Editable GLB differs from exact approved S05 artifact')
    return dict(status='FAIL' if errors else 'PASS',errors=errors,glbSha256=actual,exactUnaffectedMeshes=len(old)-1,scope='All original materials/images and1105 unrelated mesh arrays/bounds exact; retained pale and moved cap normals exact; new stile normals and material-scaled UV verified. No Unity runtime claim.')
