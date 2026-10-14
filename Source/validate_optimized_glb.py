"""Validate exported GLB independently against source native and baseline GLB."""
import sys,json
from pathlib import Path
import numpy as np
from pygltflib import GLTF2
from peer_culling_contract import read_visual
from visual_mesh_optimization import SEA_KEYS,retained_vertex_indices

def access(g,index):
 a=g.accessors[index];v=g.bufferViews[a.bufferView];d={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a.componentType];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a.type];size=np.dtype(d).itemsize*n
 assert v.byteStride in (None,0,size)
 return np.frombuffer(g.binary_blob(),d,count=a.count*n,offset=(v.byteOffset or 0)+(a.byteOffset or 0)).reshape(a.count,n)
old=GLTF2().load(sys.argv[1]);new=GLTF2().load(sys.argv[2]);original=read_visual(sys.argv[3]);candidate=read_visual(sys.argv[4]);ob={m.name:m for m in old.meshes};nb={m.name:m for m in new.meshes};assert set(ob)==set(nb)
maxnorm=0;rows=[]
for a,b in zip(original,candidate):
 k=(a['group'],a['material']);name='__'.join(k);p=nb[name].primitives[0];q=ob[name].primitives[0]
 v=b['vertices'][:,[0,2,1]].copy();v[:,2]*=-1
 np.testing.assert_array_equal(access(new,p.attributes.POSITION),v)
 np.testing.assert_array_equal(access(new,p.indices).reshape(-1,3),b['faces'])
 np.testing.assert_array_equal(access(new,p.attributes.COLOR_0),b['colors'])
 if k not in SEA_KEYS:
  # Compare GLB normals on every corresponding rendered corner, not unused.
  np.testing.assert_array_equal(access(old,q.attributes.TEXCOORD_0)[a['faces']],access(new,p.attributes.TEXCOORD_0)[b['faces']])
  expected=access(old,q.attributes.NORMAL)[a['faces']]
  actual=access(new,p.attributes.NORMAL)[b['faces']]
  error=float(np.max(np.abs(actual-expected)));assert error<2e-6,(k,error);maxnorm=max(maxnorm,error)
 else:
  normals=access(new,p.attributes.NORMAL);np.testing.assert_array_equal(normals,np.tile([0.,1.,0.],(len(normals),1)))
print(json.dumps(dict(status='PASS',meshes=len(nb),nativePositionColorIndicesExact=True,maximumNonSeaNormalComponentDifference=maxnorm,beforeGlbBytes=Path(sys.argv[1]).stat().st_size,afterGlbBytes=Path(sys.argv[2]).stat().st_size),indent=2))
