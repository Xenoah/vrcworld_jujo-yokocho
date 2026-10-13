"""Read-only exact visual-bark triangle versus walking-body corridor review."""
from pathlib import Path
import json,sys,time
import numpy as np
from shapely.geometry import LineString,Point,box
from shapely.strtree import STRtree
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent;sys.path.insert(0,str(root/'Source'))
from validate_crown import read_collision,clipped_projection,densified_segments
started=time.time();manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
meshes=read_collision(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
tri=[];names=[]
for mesh in meshes:
 if mesh['group'].startswith('Tree/') and mesh['material']=='Bark':
  tri.extend(mesh['triangles']);names.extend([mesh['group']]*len(mesh['triangles']))
del meshes
tri=np.asarray(tri);low=tri.min(axis=1);high=tri.max(axis=1)
tree=STRtree([box(a[0]-1e-6,a[1]-1e-6,b[0]+1e-6,b[1]+1e-6) for a,b in zip(low,high)])
checks=0;hits=[];counts={}
def probe(category,name,footprint,lo,hi,start=None,end=None):
 global checks
 checks+=1;counts[category]=counts.get(category,0)+1
 ids=tree.query(footprint);ids=ids[(high[ids,2]>=lo)&(low[ids,2]<=hi)]
 found=[]
 for i in ids:
  shape=clipped_projection(tri[i:i+1],lo,hi)
  if shape is not None and shape.intersects(footprint):found.append(int(i))
 if found:
  row={'category':category,'route':name,'triangleCount':len(found),'groups':sorted(set(names[i] for i in found)),'triangleIds':found[:20]}
  if start is not None:row['start']=np.asarray(start).tolist()
  if end is not None:row['end']=np.asarray(end).tolist()
  hits.append(row)

def corridor(category,name,points,radius):
 for a,b in densified_segments(np.asarray(points)):
  footprint=LineString([a[:2],b[:2]]).buffer(radius,quad_segs=8)
  probe(category,name,footprint,min(a[2],b[2])+.055,max(a[2],b[2])+2.2,a,b)

for route in manifest['crownStairs']['routes']:
 corridor('crown_full_lane',route['name'],route['points'],max(.25,float(route.get('width',2.8))/2))
for route in manifest['navigationPaths']:
 corridor('legacy_route_body',route['id'],[[*xy,route['z']] for xy in route['points']],.25)
z=next(floor['z'] for floor in manifest['floors'] if floor['level']=='L2')
ring=manifest.get('mainRingNavigation')
corridor('main_ring_body','MainRing',[[*xy,ring['z']] for xy in ring['points']] if ring else [[18*np.cos(a),18*np.sin(a),z] for a in np.linspace(0,2*np.pi,241)],.25)
for stair in manifest['stairs']:
 start=np.asarray(stair['start']);direction=np.r_[stair['dir'],0]
 run=stair['plan_run'];landing=stair['intermediate_landing'];flight=(run-landing)/2
 points=[start+direction*s+[0,0,h] for s,h in [(0,0),(flight,stair['rise']/2),(flight+landing,stair['rise']/2),(run,stair['rise'])]]
 corridor('legacy_stair_body',stair['id'],points,.25)
for seat in manifest['stations']:
 p=np.asarray(seat['position']);exit=np.asarray(seat['exit']);floor=p[2]-.70
 probe('guest_seated',seat['name'],Point(p[:2]).buffer(.28,quad_segs=12),p[2]+.12,p[2]+1.10,p,p)
 probe('guest_exit',seat['name'],Point(exit[:2]).buffer(.25,quad_segs=12),floor+.055,floor+2.2,exit,exit)
 probe('guest_transfer_torso',seat['name'],LineString([p[:2],exit[:2]]).buffer(.25,quad_segs=12),floor+.76,floor+1.95,p,exit)
result={'status':'PASS' if not hits else 'FAIL','version':manifest['version'],'barkTriangles':len(tri),'sweeps':checks,'scopeCounts':counts,'hitSweeps':len(hits),'hits':hits,'seconds':round(time.time()-started,2),'scope':'Actual Tree/Bark surfaces. Crown: full nominal lane width and2.2m headroom. Legacy routes/stairs/ring: .25m radius,2.2m headroom. Guest seated/exit/transfer: explicit torso/body regions. Not foliage, Unity or inside-only volume containment.'}
(root/'Docs/bark_clearance_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(bool(hits))
