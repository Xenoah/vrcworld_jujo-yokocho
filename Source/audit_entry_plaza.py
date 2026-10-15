"""Offline actual-mesh audit. Does not claim Unity physics, avatar or VRChat validation."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from shapely import wkt
from shapely.geometry import Point,Polygon,LineString,box,MultiPoint
from shapely.ops import unary_union
from entry_geometry_io import read_geometry,parse_geometry
BASE=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path(__file__).resolve().parent.parent
cfg=json.loads((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlaza.json').read_text());manifest=json.loads((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());R=cfg['clearance']['radius'];H=cfg['clearance']['headroom'];EPS=cfg['clearance']['footTolerance']
meshes={kind:read_geometry(BASE,kind) for kind in ['Visual','Collision']}
meshes['AddedVisual']=parse_geometry((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlazaMeshes.bytes').read_bytes())
for ms in meshes.values():
 for m in ms:
  m['tri']=m['vertices'][m['faces']];m['lo']=m['tri'].min(axis=1);m['hi']=m['tri'].max(axis=1)
def clip(poly,k,value,greater):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  a=p[k]>=value if greater else p[k]<=value;b=q[k]>=value if greater else q[k]<=value
  if a:out.append(p)
  if a!=b:out.append(p+(q-p)*(value-p[k])/(q[k]-p[k]))
 return out

def corners(b):
 c=np.array(b['center']);s=np.array(b['size'])/2;a=np.array(b['axes']).reshape(3,3)
 return np.array([c+(np.array([i,j,k])*s)@a for i in [-1,1] for j in [-1,1] for k in [-1,1]])
def obstruction(region,z,include_added=True,only_added=False):
 bounds=np.array([region.bounds[:2],region.bounds[2:]]);hit=[]
 for kind,ms in meshes.items():
  if (kind=='AddedVisual' and not include_added) or (only_added and kind!='AddedVisual'):continue
  for m in ms:
   keep=np.all(m['hi']>[*bounds[0],z+EPS],axis=1)&np.all(m['lo']<[*bounds[1],z+H],axis=1)
   ps=[]
   for t in m['tri'][keep]:
    p=clip(list(t),2,z+EPS,True);p=clip(p,2,z+H,False)
    if len(p)<3:continue
    p=Polygon(np.array(p)[:,:2]);p=p.buffer(.0005) if p.area<1e-9 else p.buffer(0)
    if p.intersects(region):ps.append(p.intersection(region))
   if ps:
    area=unary_union(ps).area
    if area>1e-6:hit.append(dict(type=kind,name=m['group'],area=area))
 for b in ([] if only_added else manifest['solidBoxes'])+(cfg['solidBoxes'] if include_added else []):
  ps=corners(b)
  if ps[:,2].max()<=z+EPS or ps[:,2].min()>=z+H:continue
  p=MultiPoint(ps[:,:2]).convex_hull
  area=p.intersection(region).area
  if area>1e-6:hit.append(dict(type='Box',name=b['name'],area=area))
 return hit

def support(x,y,z):
 # Native collision top surfaces only, not a WKT assertion.
 best=None;name=None
 for m in meshes['Collision']:
  keep=(m['lo'][:,0]<=x+1e-5)&(m['hi'][:,0]>=x-1e-5)&(m['lo'][:,1]<=y+1e-5)&(m['hi'][:,1]>=y-1e-5)&(m['lo'][:,2]<=z+.08)&(m['hi'][:,2]>=z-.15)
  ts=m['tri'][keep]
  if not len(ts):continue
  a=ts[:,0];b=ts[:,1]-a;c=ts[:,2]-a;det=b[:,0]*c[:,1]-b[:,1]*c[:,0];ok=np.abs(det)>1e-8
  for aa,bb,cc,dd in zip(a[ok],b[ok],c[ok],det[ok]):
   rel=np.array([x,y])-aa[:2];u=(rel[0]*cc[1]-rel[1]*cc[0])/dd;v=(bb[0]*rel[1]-bb[1]*rel[0])/dd
   if u>=-1e-5 and v>=-1e-5 and u+v<=1+1e-5:
    zz=aa[2]+u*bb[2]+v*cc[2]
    if z-.15<=zz<=z+.08 and (best is None or zz>best):best=float(zz);name=m['group']
 return best,name

def tri_box_intersects(t,center,half):
 # Complete separating-axis triangle/AABB test. Vectorized candidate triangles.
 q=t-center
 for ax in np.eye(3):
  p=q@ax;r=np.abs(ax)@half
  if len(q)==0:return np.zeros(0,bool)
  # Keep result rather than early removal to preserve triangle indexes.
 result=np.ones(len(q),bool)
 axes=[np.repeat(ax[None,:],len(q),axis=0) for ax in np.eye(3)]
 edges=[q[:,1]-q[:,0],q[:,2]-q[:,1],q[:,0]-q[:,2]]
 axes.append(np.cross(edges[0],edges[1]))
 for edge in edges:
  for ax in np.eye(3):axes.append(np.cross(edge,ax))
 for ax in axes:
  p=np.einsum('tvi,ti->tv',q,ax);r=np.abs(ax)@half
  result&=(p.min(axis=1)<=r+1e-7)&(p.max(axis=1)>=-r-1e-7)
 return result

fail=[];placements=[]
for b in cfg['solidBoxes']:
 c=np.array(b['center']);s=np.array(b['size'])/2;lo=c-s;hi=c+s
 # Ignore intended floor surface contact (first 25 mm), but not furniture/structural clashes above it.
 lo[2]=max(lo[2],134.025);center=(lo+hi)/2;half=(hi-lo)/2;hits=[]
 for kind,ms in meshes.items():
  if kind=='AddedVisual':continue
  for m in ms:
   keep=np.all(m['hi']>lo+1e-5,axis=1)&np.all(m['lo']<hi-1e-5,axis=1)
   if np.any(keep) and tri_box_intersects(m['tri'][keep],center,half).any():hits.append(kind+':'+m['group'])
 for old in manifest['solidBoxes']:
  ps=corners(old);oldlo=ps.min(axis=0);oldhi=ps.max(axis=0)
  if np.all(oldhi>lo+1e-5) and np.all(oldlo<hi-1e-5):
   # Convex XY footprint overlap, with vertical overlap: conservative for angled boxes.
   p=MultiPoint(ps[:,:2]).convex_hull
   if p.intersection(box(lo[0],lo[1],hi[0],hi[1])).area>1e-5:hits.append('Box:'+old['name'])
 support_points=[(x,y) for x in np.linspace(lo[0]+.01,hi[0]-.01,3) for y in np.linspace(lo[1]+.01,hi[1]-.01,3)]
 supports=[support(x,y,134) for x,y in support_points];supported=all(s[0] is not None and abs(s[0]-134)<.04 for s in supports)
 rec=dict(name=b['name'],clearOfCore=not hits,coreHits=hits,floorSupported=supported,supportProbes=len(supports),nativeFloorGroups=sorted(set(s[1] for s in supports if s[1])))
 placements.append(rec)
 if hits or not supported:fail.append(rec)
routes=[]
for route in cfg['routes']:
 path=LineString(route['points']);region=path.buffer(R,cap_style=1,join_style=1);hits=obstruction(region,route['floor']);floor=wkt.loads(next(f['wkt'] for f in manifest['floors'] if f['z']==route['floor']));outside=region.difference(floor).area
 probes=[]
 for dist in np.linspace(0,path.length,max(2,math.ceil(path.length/.2))):
  p=path.interpolate(dist)
  for dx,dy in [(0,0),(R,0),(-R,0),(0,R),(0,-R)]:probes.append(support(p.x+dx,p.y+dy,route['floor']))
 supported=all(s[0] is not None and abs(s[0]-route['floor'])<.04 for s in probes)
 rec=dict(id=route['id'],lengthM=round(path.length,3),radiusM=R,headroomM=H,obstructions=hits,outsideFloorArea=outside,nativeSupportProbeCount=len(probes),supported=supported,pass_=not hits and outside<1e-5 and supported);routes.append(rec)
 if not rec['pass_']:fail.append(rec)
standing=[]
allpoints=cfg['standingPoints']+[dict(id='Spawn'+str(i),position=s['position']) for i,s in enumerate(manifest['spawns'])]+[dict(id='WarpDestination'+w['id'],position=w['destination']) for w in cfg['warps']]
for p in allpoints:
 x,y,z=p['position'];z=round(z) if abs(z-round(z))<=.081 else z;region=Point(x,y).buffer(R,resolution=32);hits=obstruction(region,z);probes=[support(x+R*math.cos(a),y+R*math.sin(a),z) for a in np.linspace(0,math.tau,17)]+[support(x,y,z)]
 good=not hits and all(s[0] is not None and abs(s[0]-z)<.04 for s in probes);rec=dict(id=p['id'],position=p['position'],obstructions=hits,nativeSupportProbes=len(probes),pass_=good);standing.append(rec)
 if not good:fail.append(rec)
# Differential preservation: added geometry must not narrow any original declared
# corridor, or encroach on any of the 49 seats' exit capsules.
retained=[]
for path in manifest['navigationPaths']+[manifest['mainRingNavigation']]:
 region=LineString(path['points']).buffer(max(R,path['width']/2),cap_style=1,join_style=1)
 hits=obstruction(region,path['z'],only_added=True);rec=dict(id=path['id'],originalWidthM=path['width'],addedObstructions=hits,pass_=not hits);retained.append(rec)
 if hits:fail.append(rec)
for seat in manifest['stations']:
 x,y,z=seat['exit'];z=round(z);hits=obstruction(Point(x,y).buffer(R),z,only_added=True);rec=dict(id=seat['name']+'_exit',addedObstructions=hits,pass_=not hits);retained.append(rec)
 if hits:fail.append(rec)
# Entire independent furniture assemblies must not intersect one another.
# Expected joinery contacts inside one assembly and guideboard hanging plaques
# are intentional. The stump tabletop is part of its stump assembly.
def assembly(name):
 a=name.split('/')[0]
 return 'Guideboard' if a=='WarpPlaques' else ('StumpTable' if a=='StumpTableTop' else a)
assembly_overlaps=[]
for i,a in enumerate(cfg['solidBoxes']):
 for b in cfg['solidBoxes'][i+1:]:
  if assembly(a['name'])==assembly(b['name']):continue
  ac=np.array(a['center']);ah=np.array(a['size'])/2;bc=np.array(b['center']);bh=np.array(b['size'])/2
  overlap=np.minimum(ac+ah,bc+bh)-np.maximum(ac-ah,bc-bh)
  if np.all(overlap>1e-5):assembly_overlaps.append(dict(a=a['name'],b=b['name'],overlapM=overlap.tolist()))
if assembly_overlaps:fail.append(dict(independentFurnitureOverlaps=assembly_overlaps))

# Preserve the full existing roster and exact core source fingerprint.
sha=hashlib.sha256((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_bytes()).hexdigest();preserved=sha==cfg['preservation']['coreManifestSha256'] and manifest['stations'].__len__()==49 and manifest['teleports']==cfg['preservation']['teleports'] and manifest['spawns']==cfg['preservation']['spawns']
if not preserved:fail.append('Core fingerprint/roster changed')
report=dict(inputSha256=dict(coreManifest=sha,entryConfig=hashlib.sha256((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlaza.json').read_bytes()).hexdigest(),entryNative=hashlib.sha256((OUT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza/Data/EntryPlazaMeshes.bytes').read_bytes()).hexdigest()),status='FAIL' if fail else 'PASS',scope='Offline native visual/collision triangle and explicit oriented-box analysis. Not Unity physics, room-scale VR, or VRChat runtime validation.',radiusM=R,headroomM=H,floorContactToleranceM=EPS,triangleAabbSAT=True,addedNativeTrianglesIncluded=True,coreRosterPreserved=preserved,newWarpCount=len(cfg['warps']),newLights=cfg['addedLights'],newStations=cfg['addedStations'],placements=placements,routes=routes,standing=standing,originalRoutesAndSeatExits=retained,independentFurnitureOverlapCount=len(assembly_overlaps),failures=fail)
(OUT/'Docs/entry-plaza-geometry-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'failures':fail,'placements':len(placements),'routes':len(routes),'standing':len(standing)},ensure_ascii=False,indent=2));raise SystemExit(bool(fail))
