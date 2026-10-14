"""Source-triangle viewpoint diagnostic, not a physics-engine capsule test."""
import sys,json,math,hashlib,itertools
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,Point,MultiPoint
from shapely.ops import unary_union,nearest_points
from peer_culling_contract import read_visual
root=Path(sys.argv[1]);data=root/'Assets/TreeTopYokocho/Data';m=json.loads((data/'WorldManifest.json').read_text())
c=read_visual(data/'CollisionMeshes.bytes');v=read_visual(data/'VisualMeshes.bytes')
floor=[];labels=[];walls=[]
for b in c:
 q=b['vertices'][b['faces']].astype(float)
 if b['group'].startswith(('Floors/','Ramps/')):
  good=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])[:,2]>1e-9
  for i in np.flatnonzero(good):floor.append(q[i]);labels.append([b['group'],int(i)])
 if b['group'].startswith('Safety/'):walls.extend(q)
floor=np.asarray(floor);wall=np.asarray(walls);flo=floor.min(axis=1);fhi=floor.max(axis=1);wlo=wall.min(axis=1);whi=wall.max(axis=1)
sea=unary_union([Polygon(t[:,:2]) for b in v if b['group'].startswith('Landscape/Sea_') for t in b['vertices'][b['faces']]])


mesh_sources=[]
for kind, batches in [('collision',c),('visual',v)]:
 for b in batches:
  vertices=b['vertices'];mesh_sources.append((kind,b['group'],b['material'],vertices,b['faces'],vertices.min(axis=0),vertices.max(axis=0)))
box_triangles=[]
unit=np.asarray(list(itertools.product([-1,1],repeat=3)),float)
boxfaces=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
for b in m['solidBoxes']:
 axes=np.asarray(b.get('axes',np.eye(3).reshape(-1)),float).reshape(3,3);center=np.asarray(b['center']);size=np.asarray(b['size']);verts=(unit*size/2)@axes+center
 box_triangles.append((b,verts[boxfaces],verts.min(axis=0),verts.max(axis=0),axes))

def clipped_to_slab(poly,zlo,zhi):
 for z,sign in [(zlo,1),(zhi,-1)]:
  output=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   inside_a=(a[2]-z)*sign>=0;inside_b=(b[2]-z)*sign>=0
   if inside_a:output.append(a)
   if inside_a!=inside_b:output.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
  poly=output
  if not poly:break
 return poly

def body_contacts(p,base,radius):
 low=np.r_[p[:2]-radius,base+.06];high=np.r_[p[:2]+radius,base+2.2];center=Point(p[:2]);contacts=[];tested=0
 def triangles_hit(triangles):
  nonlocal tested
  selected=np.flatnonzero(np.all(triangles.min(axis=1)<=high,axis=1)&np.all(triangles.max(axis=1)>=low,axis=1))
  for index in selected:
   tested+=1;poly=clipped_to_slab(list(triangles[index].astype(float)),low[2],high[2])
   if poly and MultiPoint(np.asarray(poly)[:,:2]).convex_hull.distance(center)<radius-1e-6:return int(index)
  return None
 for kind,group,material,vertices,faces,blo,bhi in mesh_sources:
  if np.any(blo>high) or np.any(bhi<low):continue
  hit=triangles_hit(vertices[faces])
  if hit is not None:contacts.append(dict(kind=kind,group=group,material=material,triangle=hit))
 for b,tri,blo,bhi,axes in box_triangles:
  if np.any(blo>high) or np.any(bhi<low):continue
  hit=triangles_hit(tri);middle=np.r_[p[:2],(low[2]+high[2])/2];local=(middle-np.asarray(b['center']))@axes.T
  contained=np.all(np.abs(local)<np.asarray(b['size'])/2)
  if hit is not None or contained:contacts.append(dict(kind='explicitBox',name=b['name'],triangle=hit,centerContained=bool(contained)))
 return dict(clear=not contacts,contacts=contacts,bodyZ=[float(low[2]),float(high[2])],testedTriangleCandidates=tested,visualAndCollisionMeshes=len(mesh_sources),explicitBoxes=len(box_triangles))

def check(sample):
 p=np.asarray(sample['position']);hits=[];radius=.25
 for theta in [None,*np.linspace(0,math.tau,16,endpoint=False)]:
  xy=p[:2] if theta is None else p[:2]+radius*np.array([math.cos(theta),math.sin(theta)])
  candidate=np.flatnonzero(np.all(flo[:,:2]<=xy+1e-7,axis=1)&np.all(fhi[:,:2]>=xy-1e-7,axis=1)&(flo[:,2]<=p[2]+.26)&(fhi[:,2]>=p[2]-.26))
  found=[]
  for i in candidate:
   q=floor[i];e=q[1,:2]-q[0,:2];h=q[2,:2]-q[0,:2];ab=np.linalg.solve(np.column_stack([e,h]),xy-q[0,:2]);bary=np.r_[1-ab.sum(),ab]
   z=float(bary@q[:,2])
   if min(bary)>=-1e-7 and abs(z-p[2])<=.26:found.append((z,int(i),bary.tolist()))
  if not found:return dict(supported=False,reason='Body footprint support probe missed',sample=sample,probeXY=xy.tolist())
  z,i,bary=min(found,key=lambda x:abs(x[0]-p[2]));hits.append(dict(xy=xy.tolist(),z=z,triangle=labels[i],barycentric=bary))
 # Entire projected disk support, not just the radial probes. Use only
 # upward triangles wholly inside the allowed tread-height slab.
 support_ids=np.flatnonzero(np.all(flo[:,:2]<=p[:2]+radius,axis=1)&np.all(fhi[:,:2]>=p[:2]-radius,axis=1)&(flo[:,2]>=p[2]-.26)&(fhi[:,2]<=p[2]+.26))
 domain=unary_union([Polygon(floor[i,:,:2]) for i in support_ids]);center=Point(p[:2])
 clearance=domain.boundary.distance(center)
 if not domain.covers(center) or clearance<radius-1e-6:return dict(supported=False,reason='Continuous footprint support domain too narrow',sample=sample,clearance=clearance)
 base=max(x['z'] for x in hits);ids=np.flatnonzero(np.all(wlo[:,:2]<=p[:2]+radius,axis=1)&np.all(whi[:,:2]>=p[:2]-radius,axis=1)&(wlo[:,2]<base+1.8)&(whi[:,2]>min(x['z'] for x in hits)+.05))
 for i in ids:
  if MultiPoint(wall[i,:,:2]).convex_hull.distance(Point(p[:2]))<radius-1e-6:return dict(supported=False,reason='Footprint intersects projected safety wall',sample=sample)
 body=body_contacts(p,base,radius)
 if not body['clear']:return dict(supported=False,reason='Source mesh or explicit box body contact',sample=sample,body=body)
 eye=[float(p[0]),float(p[1]),base+1.65];target=nearest_points(Point(p[:2]),sea)[1];distance=math.hypot(Point(p[:2]).distance(sea),eye[2]+4.019999980926514)
 return dict(supported=True,sample=sample,eye=eye,lookAt=[target.x,target.y,-4.019999980926514],distanceToSeaMetres=distance,radius=radius,footprintProbeCount=len(hits),supportHeightRange=[min(x['z'] for x in hits),base],supportEvidence=hits,sourceSafetyWallClearance=True,continuousSupportClearanceMetres=clearance,continuousDiskSupport=True,body=body)
ordered=sorted(m['floorTests'],key=lambda s:math.hypot(Point(s['position'][:2]).distance(sea),s['position'][2]+1.65+4.02))
rejected=[];accepted=None
for sample in ordered:
 result=check(sample)
 if result['supported']:accepted=result;break
 rejected.append(result)
report=dict(sourceSha256={name:hashlib.sha256((data/name).read_bytes()).hexdigest() for name in ['VisualMeshes.bytes','CollisionMeshes.bytes','WorldManifest.json']},nearestSupportedSampledView=accepted,rejectedNearerSamples=rejected,requestedCloudSeaCamera=check(dict(id='RequestedCloudSea',position=[0,-40,134])),scope='17 support-height probes plus continuous projected0.25m disk containment in union of upward source floor triangles wholly inside±0.26m tread-height slab; conservative projected safety-wall clearance for1.8m body; not Unity physics/capsule sweep. All actual visual+collision triangles and explicit boxes are tested for intersection with finite vertical cylinder radius0.25m, from highest support+.06m to+2.2m, using Z-slab triangle clipping and projected-distance narrow phase. No visibility/occlusion claim.')
print(json.dumps(report,indent=2))
