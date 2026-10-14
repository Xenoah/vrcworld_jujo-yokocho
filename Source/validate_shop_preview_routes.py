"""Camera-only source diagnostics: connect shop survey eyes to authored routes.
No scene geometry is changed. Not Unity avatar/capsule-sweep certification.
"""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from shapely.geometry import Point,LineString,box
from validate_visual_routes import read_payload,contact_points
from validate_crown import Rays,box_triangles

def main(root):
 root=root.resolve();m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());cameras=json.loads((root/'Source/detail_cameras.json').read_text())
 batches=[]
 for fn in ['VisualMeshes.bytes','CollisionMeshes.bytes']:batches.extend(read_payload(root/'Assets/TreeTopYokocho/Data'/fn,fn))
 floors=np.concatenate([b['triangles'] for b in batches if b['scope']=='CollisionMeshes.bytes' and b['name'].startswith(('Floors/','Ramps/'))]);rays=Rays(floors)
 boxes=[(b['name'],box_triangles(b)) for b in m['solidBoxes']];rows=[]
 for name,entry in cameras.items():
  if not name.startswith('survey_'):continue
  z=entry['standingFloorZ'];cam=entry['camera'];point=Point(cam[:2]);candidates=[]
  for route in m['navigationPaths']+[m['mainRingNavigation']]:
   if abs(route['z']-z)>.001:continue
   line=LineString(route['points']);start=line.interpolate(line.project(point));candidates.append((start.distance(point),route['id'],list(start.coords[0])))
  attempts=[]
  for length,route,start in sorted(candidates):
   if length>12:continue
   line=LineString([start,cam[:2]]);foot=line.buffer(.25,quad_segs=12);lo=foot.bounds[:2];hi=foot.bounds[2:];contacts=[]
   for b in batches:
    if not box(*b['bounds_low'][:2],*b['bounds_high'][:2]).intersects(foot):continue
    ids=np.where((b['high'][:,2]>=z+.06)&(b['low'][:,2]<=z+2.2)&(b['high'][:,0]>=lo[0])&(b['low'][:,0]<=hi[0])&(b['high'][:,1]>=lo[1])&(b['low'][:,1]<=hi[1]))[0]
    if any(len(contact_points(b['triangles'][i],foot,z+.06,z+2.2)) for i in ids):contacts.append(b['name'])
   for label,tris in boxes:
    if any(len(contact_points(t,foot,z+.06,z+2.2)) for t in tris):contacts.append('solidBoxes/'+label)
   support=[]
   if not contacts:
    for fraction in np.linspace(0,1,max(2,math.ceil(length/.1)+1)):
     center=np.array(start)*(1-fraction)+np.array(cam[:2])*fraction
     for angle in [None,*np.linspace(0,math.tau,8,endpoint=False)]:
      xy=center if angle is None else center+.25*np.array([math.cos(angle),math.sin(angle)])
      hit=rays.hit([*xy,z+.75],[0,0,-1],1.5);support.append(hit)
   passed=not contacts and support and all(v is not None and abs(v-.75)<.035 for v in support)
   attempt={'route':route,'routePoint':[*start,z+1.65],'lengthMetres':length,'contacts':contacts,'supportRays':len(support),'supportPassed':bool(support) and all(v is not None and abs(v-.75)<.035 for v in support),'passed':bool(passed)};attempts.append(attempt)
   if passed:break
  rows.append({'camera':name,'position':cam,'passed':any(a['passed'] for a in attempts),'attempts':attempts})
 sources=['Source/detail_cameras.json','Assets/TreeTopYokocho/Data/WorldManifest.json','Assets/TreeTopYokocho/Data/VisualMeshes.bytes','Assets/TreeTopYokocho/Data/CollisionMeshes.bytes']
 report={'status':'PASS' if len(rows)==8 and all(x['passed'] for x in rows) else 'FAIL','scope':'Straight camera connectors to authored route centerlines, maximum12m: full buffered footprint against actual triangle surfaces and boxes, floor rays at<=.1m spacing. Not inside-only solid containment, arbitrary free-roomscale movement, Unity physics or avatar certification.','radius':.25,'bodyHeight':2.2,'bodyLowerOffset':.06,'sourceSha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources},'checks':rows}
 (root/'Docs/shop_preview_route_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report['status']!='PASS'
if __name__=='__main__':raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]))
