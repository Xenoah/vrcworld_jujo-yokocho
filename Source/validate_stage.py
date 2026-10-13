"""Check the actual Noh-stage preview mesh and physical deck, offline only."""
from pathlib import Path
import json,sys
import numpy as np
from shapely.geometry import Polygon,Point
from shapely import wkt
from validate_crown import read_collision,Rays
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());stage=m['nohStage'];checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
visual=read_collision(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
tri=np.concatenate([x['triangles'] for x in visual if x['group'].startswith('Stage/Noh/')]);rays=Rays(tri)
center=np.array(stage['center']);right=np.array(stage['right']);front=np.array(stage['front'])
physical=wkt.loads(next(x['wkt'] for x in m['floors'] if x['level']=='L2'))
check('Continuous physical deck covers stage footprint',physical.covers(Polygon(stage['deckUnionPolygon'])))
posts=[]
for b in stage['solidBoxes']:
 c=np.array(b['center']);axes=np.array(b['axes']).reshape(3,3);s=np.array(b['size'])
 posts.append(Polygon([(c+axes[0]*x*s[0]/2+axes[1]*y*s[1]/2)[:2] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]).buffer(.25))
misses=[];samples=0
for x in np.arange(-1.6,1.61,.20):
 for y in np.arange(-1.6,1.61,.20):
  p=center+right*x+front*y
  if any(q.covers(Point(p[:2])) for q in posts):continue
  samples+=1;hit=rays.hit(p+[0,0,.05],[0,0,1],2.55)
  if hit is not None:misses.append([p.tolist(),hit])
check('Actual stage mesh has at least2.6m overhead in central performance area',not misses,dict(samples=samples,misses=misses[:5]))
views=[]
for direction in [right,-right,front,-front]:
 p=center+direction*3.4+[0,0,1.55];d=-direction;hit=rays.hit(p,d,3.4)
 views.append(hit)
check('Four open sides have unblocked eye-level center sightlines',all(x is None for x in views),views)
check('Four support pillars and no eye-level wall',stage['stats']['posts']==4 and stage['stats']['opaqueEyeLevelWalls']==0)
report=dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',scope='Offline actual geometry; Unity/VRChat runtime not executed.',checks=checks)
(root/'Docs/stage_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(report['status']!='PASS')
