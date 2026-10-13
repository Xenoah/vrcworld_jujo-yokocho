"""Read-only exact visual-bark triangle versus walking-body corridor review."""
from pathlib import Path
import json,sys,time
import numpy as np
from shapely.geometry import LineString,box
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
checks=0;hits=[]
for route in manifest['crownStairs']['routes']:
 points=np.asarray(route['points'])
 for a,b in densified_segments(points):
  checks+=1;footprint=LineString([a[:2],b[:2]]).buffer(max(.25,float(route.get('width',2.8))/2),quad_segs=8);lo=min(a[2],b[2])+.055;hi=max(a[2],b[2])+2.2
  ids=tree.query(footprint);ids=ids[(high[ids,2]>=lo)&(low[ids,2]<=hi)]
  found=[]
  for i in ids:
   shape=clipped_projection(tri[i:i+1],lo,hi)
   if shape is not None and shape.intersects(footprint):found.append(int(i))
  if found:hits.append({'route':route['name'],'start':a.tolist(),'end':b.tolist(),'triangleCount':len(found),'groups':sorted(set(names[i] for i in found)),'triangleIds':found[:20]})
result={'status':'PASS' if not hits else 'FAIL','version':manifest['version'],'barkTriangles':len(tri),'sweeps':checks,'hitSweeps':len(hits),'hits':hits,'seconds':round(time.time()-started,2),'scope':'Actual visual Tree/Bark triangle surfaces versus full nominal floor-width lane envelope, height2.2 swept corridor; not foliage, Unity or volumetric inside-only containment'}
(root/'Docs/bark_clearance_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(bool(hits))
