"""Independent native/GLB preservation evidence; no production mutation calls."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from pygltflib import GLTF2
from peer_culling_contract import read_visual,summarize
from city_roof_caps_test_fixture import restore_city_caps
from visual_optimization_test_fixture import restored_prior_fixture,native_sha

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def access(g,index):
    a=g.accessors[index];v=g.bufferViews[a.bufferView];d={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a.componentType];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a.type]
    assert v.byteStride in (None,0,np.dtype(d).itemsize*n)
    return np.frombuffer(g.binary_blob(),d,count=a.count*n,offset=(v.byteOffset or 0)+(a.byteOffset or 0)).reshape(a.count,n)
oldroot,newroot=map(Path,sys.argv[1:3]);rel=Path('Assets/TreeTopYokocho/Data');old=read_visual(oldroot/rel/'VisualMeshes.bytes');new=read_visual(newroot/rel/'VisualMeshes.bytes')
assert [(x['group'],x['material']) for x in old]==[(x['group'],x['material']) for x in new]
g0=GLTF2().load(str(oldroot/'Source/TreeTopYokocho.glb'));g1=GLTF2().load(str(newroot/'Source/TreeTopYokocho.glb'));m0={m.name:m for m in g0.meshes};m1={m.name:m for m in g1.meshes};changed=[]
assert g0.materials==g1.materials and g0.textures==g1.textures and g0.samplers==g1.samplers
assert g0.nodes==g1.nodes and g0.scenes==g1.scenes
for a,b in zip(old,new):
    k=(a['group'],a['material']);mask=np.ones(len(a['faces']),bool)
    if k==('Landscape/DetailCityRoofs','DarkTimber'):
        # Independent source-order cap identification, not optimize/selection.
        for h in range(139):
            for box in range(3,9):mask[(h*9+box)*12+2:(h*9+box)*12+4]=False
        keep=np.unique(a['faces'][mask]);remap=np.full(len(a['vertices']),-1);remap[keep]=np.arange(len(keep))
        np.testing.assert_array_equal(b['faces'],remap[a['faces'][mask]])
        for attr in ('vertices','uv','colors'):np.testing.assert_array_equal(b[attr],a[attr][keep])
        changed.append(dict(before=summarize(a),after=summarize(b)))
    else:assert summarize(a)==summarize(b),k
    for attr in ('vertices','uv','colors'):np.testing.assert_array_equal(a[attr][a['faces'][mask]],b[attr][b['faces']])
    np.testing.assert_array_equal(a['vertices'].min(0),b['vertices'].min(0));np.testing.assert_array_equal(a['vertices'].max(0),b['vertices'].max(0))
    name='__'.join(k);p=m0[name].primitives[0];q=m1[name].primitives[0]
    assert p.material==q.material and p.mode==q.mode and p.extensions==q.extensions
    np.testing.assert_array_equal(access(g1,q.indices).reshape(-1,3),b['faces'])
    for attr in ('NORMAL','TEXCOORD_0','COLOR_0','POSITION'):
        np.testing.assert_array_equal(access(g0,getattr(p.attributes,attr))[a['faces'][mask]],access(g1,getattr(q.attributes,attr))[b['faces']])
assert len(changed)==1
for name in ('CollisionMeshes.bytes','CollisionMeshes.bytes.gz'):assert sha(oldroot/rel/name)==sha(newroot/rel/name)
a=json.loads((oldroot/rel/'WorldManifest.json').read_text());b=json.loads((newroot/rel/'WorldManifest.json').read_text())
changed_fields=[k for k in set(a)|set(b) if a.get(k)!=b.get(k)];assert set(changed_fields)=={'features','visualTriangles','meshOptimization'}
restored,manifest=restore_city_caps(new,b);assert native_sha(restored)==sha(oldroot/rel/'VisualMeshes.bytes')
original,_=restored_prior_fixture(restored,manifest)
report=dict(status='PASS',changedBatches=changed,allOther1057BatchesByteExact=True,survivingCornerOrderPositionUvColorAndGlbNormalBitsExact=True,allBoundsExact=True,glbMaterialsNodesAndPrimitiveRoutingExact=True,collisionRawAndGzipByteExact=True,seatsAndNavigationExact=True,stations=len(b['stations']),changedManifestFields=changed_fields,originalWholeWorldReconstructedSha256=native_sha(original),bytes={name:dict(before=(oldroot/path).stat().st_size,after=(newroot/path).stat().st_size,saved=(oldroot/path).stat().st_size-(newroot/path).stat().st_size) for name,path in [('native',rel/'VisualMeshes.bytes'),('gzip',rel/'VisualMeshes.bytes.gz'),('glb',Path('Source/TreeTopYokocho.glb'))]},nativeSha256=sha(newroot/rel/'VisualMeshes.bytes'),glbSha256=sha(newroot/'Source/TreeTopYokocho.glb'),limitations='Source/native/GLB proof; no Unity runtime, GPU timing, compressed-mesh pixel or GI bake identity claim.')
(newroot/'Measured/preservation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
