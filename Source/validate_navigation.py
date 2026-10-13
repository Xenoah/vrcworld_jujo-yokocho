"""Independent static-collider navigation test. Not a CharacterController simulation.
Slices actual barrier triangle meshes at foot/waist/head height, subtracts their
volume and solid boxes, then checks radius-0.25 m standing clearance connectivity.
"""
from pathlib import Path
import json,struct,sys
import numpy as np
from shapely import wkt
from shapely.geometry import Point,Polygon,LineString
from shapely.ops import unary_union,polygonize
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
triangles=[]
with (root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').open('rb') as f:
 assert f.read(4)==b'JYWM';version,count=struct.unpack('<II',f.read(8));assert version==1
 for _ in range(count):
  names=[f.read(struct.unpack('<I',f.read(4))[0]).decode() for _ in range(2)]
  nv,ni=struct.unpack('<II',f.read(8));v=np.frombuffer(f.read(nv*12),'<f4').reshape(-1,3);f.read(nv*12)
  ix=np.frombuffer(f.read(ni*4),'<u4').reshape(-1,3)
  if names[0].startswith('Safety/'):triangles.extend(v[ix])
triangles=np.asarray(triangles);mins=triangles[:,:,2].min(axis=1);maxs=triangles[:,:,2].max(axis=1)
def section(height):
 # Authored safety geometry consists of closed 12-triangle box/prism solids.
 # Slice each solid independently: polygonizing a whole closed perimeter would
 # incorrectly fill the safe courtyard inside it.
 assert len(triangles)%12==0, 'Safety primitive format changed; update section parser'
 polys=[]
 for solid in triangles.reshape(-1,12,3,3):
  if solid[:,:,2].min()>=height or solid[:,:,2].max()<=height:continue
  lines=[]
  for tri in solid:
   ps=[]
   for a,b in zip(tri,np.roll(tri,-1,axis=0)):
    if (a[2]<height<b[2]) or (b[2]<height<a[2]):ps.append((a+(b-a)*((height-a[2])/(b[2]-a[2])))[:2])
    elif abs(a[2]-height)<1e-6:ps.append(a[:2])
   ps=list({tuple(np.round(p,5)) for p in ps})
   if len(ps)==2:lines.append(LineString(ps))
  polys.extend(polygonize(unary_union(lines)))
 return unary_union(polys)

results=[];failures=[]
for lev in m['floors']:
 z=lev['z'];floor=wkt.loads(lev['wkt']);barriers=unary_union([section(z+h) for h in [.2,1.0,1.65]])
 solids=[]
 for b in m['solidBoxes']:
  p=np.asarray(b['center']);size=np.asarray(b['size']);axes=np.asarray(b['axes']).reshape(3,3)
  if p[2]+size[2]/2<z+.1 or p[2]-size[2]/2>z+1.65:continue
  corners=[p+axes[0]*sx*size[0]/2+axes[1]*sy*size[1]/2 for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
  solids.append(Polygon(np.asarray(corners)[:,:2]))
 blocked=unary_union([barriers,*solids]);free=floor.difference(blocked).buffer(-.25)
 parts=list(free.geoms) if free.geom_type=='MultiPolygon' else ([free] if not free.is_empty else [])
 points=[]
 for seat in m['stations']:
  if abs(seat['exit'][2]-z)<.3:points.append((seat['name'],seat['exit'][:2]))
 for t in m['teleports']:
  if abs(t['destination'][2]-z)<.3:points.append((t['name'],t['destination'][:2]))
 for i,p in enumerate(m['spawns']):
  if abs(p['position'][2]-z)<.3:points.append(('spawn'+str(i),p['position'][:2]))
 if m.get('nohStage') and m['nohStage']['level']==lev['level']:
  for i,p in enumerate(m['nohStage']['floorTests']):points.append(('NohStage'+str(i),p['position'][:2]))
 memberships={name:[i for i,p in enumerate(parts) if p.buffer(.002).covers(Point(xy))] for name,xy in points}
 absent=[name for name,ids in memberships.items() if not ids];shared=set.intersection(*(set(x) for x in memberships.values())) if memberships else set()
 ok=not absent and (bool(shared) or not memberships)
 if not ok:failures.append({'level':lev['level'],'missing':absent,'memberships':memberships})
 paths=[]
 for route in m.get('navigationPaths',[]):
  if route['level']!=lev['level']:continue
  line=LineString(route['points']);obstruction=line.buffer(.25,cap_style=1).intersection(blocked)
  # Floor joins can be approached through a stair landing; only collision blockage is tested here.
  route_ok=obstruction.area<.0005;paths.append({'id':route['id'],'clear':route_ok,'obstructed_area_m2':obstruction.area})
  if not route_ok:failures.append({'path':route['id'],'obstructed_area_m2':obstruction.area})
 results.append({'level':lev['level'],'radius_m':.25,'sample_heights_m':[.2,1,1.65],'component_areas_m2':[round(p.area,3) for p in parts],'destinations_connected':ok,'destination_count':len(points),'paths':paths})
report={'status':'PASS' if not failures else 'FAIL','scope':'Offline actual-mesh horizontal standing-clearance test; not Unity/VR runtime.','levels':results,'failures':failures}
(root/'Docs/navigation_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(bool(failures))
