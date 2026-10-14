"""Independent, read-only comparison of source native export to candidate.
Usage: python measure_visual_optimization.py BEFORE AFTER REPORT
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from peer_culling_contract import read_visual,summarize,attribute_vertices
from visual_mesh_optimization import SEA_KEYS,retained_vertex_indices
from shapely.geometry import Polygon
from shapely.ops import unary_union

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boundary(b):
 f=b['faces'];e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);_,inv,count=np.unique(np.sort(e,axis=1),axis=0,return_inverse=True,return_counts=True)
 a=attribute_vertices(b)
 return sorted((a[int(i)].tobytes()+a[int(j)].tobytes()).hex() for i,j in e[count[inv]==1])
def measure(before,after):
 old=read_visual(before);new=read_visual(after)
 assert [(b['group'],b['material']) for b in old]==[(b['group'],b['material']) for b in new]
 rows=[]
 for a,b in zip(old,new):
  k=(a['group'],a['material']);kind='unchanged';extra={}
  if k in SEA_KEYS:
   assert np.all(a['vertices'][:,2]==b['vertices'][0,2]) and np.all(b['vertices'][:,2]==b['vertices'][0,2])
   assert boundary(a)==boundary(b),'Boundary position/UV/color/winding changed'
   aa=unary_union([Polygon(t[:,:2]) for t in a['vertices'][a['faces']]])
   bb=unary_union([Polygon(t[:,:2]) for t in b['vertices'][b['faces']]])
   assert aa.equals(bb),'Sea polygon domain changed'
   q=b['vertices'][b['faces']].astype(float);normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);assert np.all(normal[:,2]>0)
   # Both UV fields approximate the original source affine function x,y*.018.
   # Bound absolute storage error, independent of particular triangulation.
   error=max(float(np.max(np.abs(z['uv']-z['vertices'][:,:2].astype(float)*.018))) for z in (a,b))
   assert error<1e-5
   extra=dict(boundaryIdentical=True,domainIdentical=True,normalPositiveZ=True,maximumUvAffineStorageError=error,maximumInterpolatedUvDifferenceBound=2*error)
   kind='static-planar-sea'
  else:
   # Stronger than unordered triangle fingerprint: exact corner order,
   # multiplicity, every UV/color bit, and normal/tangent adjacency classes.
   for attr in ('vertices','uv','colors'):assert np.array_equal(a[attr][a['faces']],b[attr][b['faces']]),(k,attr)
   used=retained_vertex_indices(a['vertices'],a['faces']);remap=np.full(len(a['vertices']),-1,dtype=np.int64);remap[used]=np.arange(len(used))
   assert np.array_equal(remap[a['faces']],b['faces']),'Normal seam equivalence changed'
   if len(a['vertices'])!=len(b['vertices']):kind='unused-only'
  assert np.array_equal(a['vertices'].min(axis=0),b['vertices'].min(axis=0)) and np.array_equal(a['vertices'].max(axis=0),b['vertices'].max(axis=0)),(k,'Bounds changed')
  if kind!='unchanged':rows.append(dict(kind=kind,before=summarize(a),after=summarize(b),**extra))
 return dict(beforeSha256=sha(before),afterSha256=sha(after),beforeBytes=Path(before).stat().st_size,afterBytes=Path(after).stat().st_size,beforeVertices=sum(len(x['vertices']) for x in old),afterVertices=sum(len(x['vertices']) for x in new),beforeTriangles=sum(len(x['faces']) for x in old),afterTriangles=sum(len(x['faces']) for x in new),meshCount=len(new),changes=rows)
if __name__=='__main__':
 report=measure(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
