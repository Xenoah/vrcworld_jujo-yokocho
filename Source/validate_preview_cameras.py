"""Actual support/body checks for explicitly marked pedestrian preview positions.
Unmarked historical/aerial cameras are outside this diagnostic. No Unity simulation.
"""
import sys,json,math,hashlib
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'Source'))
import numpy as np
from shapely.geometry import Point,box
from validate_visual_routes import read_payload,contact_points
from validate_crown import Rays,box_triangles
m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());cameras=json.loads((root/'Source/detail_cameras.json').read_text());names={name:entry['standingFloorZ'] for name,entry in cameras.items() if 'standingFloorZ' in entry}
assert names,'No marked standing preview cameras'
assert all(type(z) in (float,int) and math.isfinite(z) for z in names.values())
batches=[]
for fn in ['VisualMeshes.bytes','CollisionMeshes.bytes']:batches.extend(read_payload(root/'Assets/TreeTopYokocho/Data'/fn,fn))
floors=np.concatenate([b['triangles'] for b in batches if b['scope']=='CollisionMeshes.bytes' and b['name'].startswith(('Floors/','Ramps/'))]);rays=Rays(floors)
rows=[]
for name,z in names.items():
 cam=cameras[name]['camera'];foot=Point(cam[:2]).buffer(.25,quad_segs=12);hits=[]
 support=[]
 for angle in [None,*np.linspace(0,math.tau,8,endpoint=False)]:
  p=np.array([*cam[:2],z+.75]);p+=np.zeros(3) if angle is None else [.25*math.cos(angle),.25*math.sin(angle),0]
  hit=rays.hit(p,[0,0,-1],1.5);support.append(hit)
 for b in batches:
  if not box(*b['bounds_low'][:2],*b['bounds_high'][:2]).intersects(foot):continue
  ids=np.where((b['high'][:,2]>=z+.06)&(b['low'][:,2]<=z+2.2)&(b['high'][:,0]>=cam[0]-.25)&(b['low'][:,0]<=cam[0]+.25)&(b['high'][:,1]>=cam[1]-.25)&(b['low'][:,1]<=cam[1]+.25))[0]
  for i in ids:
   if len(contact_points(b['triangles'][i],foot,z+.06,z+2.2)):
    hits.append(b['name']);break
 for b in m['solidBoxes']:
  if any(len(contact_points(t,foot,z+.06,z+2.2)) for t in box_triangles(b)):hits.append('solidBoxes/'+b['name'])
 rows.append({'camera':name,'position':cam,'supportRayDistances':support,'contacts':hits,'passed':not hits and all(x is not None and abs(x-.75)<.035 for x in support)})
report={'status':'PASS' if all(x['passed'] for x in rows) else 'FAIL','sourceSha256':{str(p):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in [Path('Source/detail_cameras.json'),Path('Assets/TreeTopYokocho/Data/WorldManifest.json'),Path('Assets/TreeTopYokocho/Data/VisualMeshes.bytes'),Path('Assets/TreeTopYokocho/Data/CollisionMeshes.bytes')]},'scope':'Offline camera standing-location support and actual visual/collision surface checks; not avatar simulation','radius':.25,'height':2.2,'lowerOffset':.06,'checks':rows}
print(json.dumps(report,indent=2));(root/'Docs/preview_camera_validation.json').write_text(json.dumps(report,indent=2)+'\n')

raise SystemExit(report['status']!='PASS')
