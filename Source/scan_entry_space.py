from entry_geometry_io import read_geometry
import numpy as np,json,sys
from pathlib import Path
from shapely.geometry import Polygon,Point,box,LineString
from shapely import wkt
from shapely.ops import unary_union
ROOT=Path(sys.argv[1]);DEST=Path(__file__).resolve().parent.parent
manifest=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());floor=wkt.loads(next(f['wkt'] for f in manifest['floors'] if f['level']=='L1'))
window=box(-12,-35,11,-25)
def clip(poly,k,value,greater):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  a=(p[k]>=value) if greater else (p[k]<=value);b=(q[k]>=value) if greater else (q[k]<=value)
  if a:out.append(p)
  if a!=b:out.append(p+(q-p)*(value-p[k])/(q[k]-p[k]))
 return out

def obstacles(z0=134.10,z1=136.2):
 out=[];meta=[]
 for kind in ['Visual','Collision']:
  for m in read_geometry(ROOT,kind):
   tri=m['vertices'][m['faces']];lo=tri.min(axis=1);hi=tri.max(axis=1)
   keep=np.all(hi>[-13,-36,z0],axis=1)&np.all(lo<[12,-24,z1],axis=1)
   ps=[]
   for t in tri[keep]:
    p=clip(list(t),2,z0,True);p=clip(p,2,z1,False)
    if len(p)<3:continue
    poly=Polygon(np.array(p)[:,:2])
    if poly.area<1e-9: poly=LineString(np.array(p)[:,:2]).buffer(.001)
    if not poly.is_valid:poly=poly.buffer(0)
    if poly.intersects(window):ps.append(poly.intersection(window))
   if ps:
    u=unary_union(ps);out.append(u);meta.append((kind,m['group'],u))
 for b in manifest['solidBoxes']:
  c=np.array(b['center']);s=np.array(b['size'])/2;a=np.array(b['axes']).reshape(3,3)
  corners=np.array([c+np.array([i,j,k])*s@a for i in [-1,1] for j in [-1,1] for k in [-1,1]])
  if corners[:,2].min()>z1 or corners[:,2].max()<z0:continue
  p=Polygon(corners[:,:2]).convex_hull
  if p.intersects(window):out.append(p);meta.append(('Box',b['name'],p))
 return unary_union(out),meta
blocked,meta=obstacles();free=floor.difference(blocked).buffer(-.325)
for y in [-33,-32.5,-32,-31.8,-31.5,-31,-30.5,-30,-29.5,-29,-28.5,-28]:
 print(y, ''.join('.' if free.covers(Point(x,y)) else '#' for x in np.arange(-10,10.01,.25)))
print('Candidates')
for x,y in [(-7,-31.8),(-7,-30.5),(-7,-32.3),(-4.5,-32),(-4.5,-31),(-6,-29.5),(4,-29),(6,-32),(0,-32)]:
 print((x,y),'floor',floor.covers(Point(x,y).buffer(.7)),'free',free.covers(Point(x,y)), 'obstacles',[(kind,n) for kind,n,p in meta if p.distance(Point(x,y))<.7])
# Pretty actual projection, not a concept plan.
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(14,8));
def draw(poly,color,alpha=1):
 for p in (poly.geoms if hasattr(poly,'geoms') else [poly]):
  if hasattr(p,'exterior'):ax.fill(*p.exterior.xy,color=color,alpha=alpha)
draw(floor.intersection(window),'#c6af87');draw(blocked.intersection(window),'#6d4938');draw(free.intersection(window),'#73a69c',.6)
for s in manifest['spawns']:ax.plot(*s['position'][:2],'bo')
for i in range(-10,11):ax.text(i,-34.6,str(i),fontsize=8)
ax.set_xlim(-12,11);ax.set_ylim(-35,-24);ax.set_aspect('equal');ax.grid();fig.savefig(DEST/'Preview/entry-actual-clearance-map.png',dpi=150)
(DEST/'Docs/entry-scan-regions.json').write_text(json.dumps({'free_wkt':free.wkt,'blocked_wkt':blocked.wkt,'floor_wkt':floor.wkt}))
