"""Actual visual triangles versus explicit seated/walking clearance envelopes.

This is not an avatar physics simulation. It checks the geometry that physics
alone cannot see, and catches decorative objects intersecting designated routes.
"""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
from shapely.geometry import Point,LineString,box
from shapely.strtree import STRtree
from validate_crown import read_collision,clipped_projection,densified_segments
from revision_contracts import (COLLISION_SHA256,metadata_sha256,
    intended_solid_box_changes,intended_lift_control_changes,
    protected_geometry_changes,main_ring_route)

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
data=root/'Assets/TreeTopYokocho/Data';started=time.time()
m=json.loads((data/'WorldManifest.json').read_text())
base=json.loads((root/'Docs/baselines/verified_layout_2.6.0.json').read_text())
failures=[];checks=[]
def check(name,ok,detail=None):
    entry={'name':name,'passed':bool(ok)}
    if detail is not None:entry['detail']=detail
    checks.append(entry)
    if not ok:failures.append(entry)
check('decorative_revision_preserves_collision',
      hashlib.sha256((data/'CollisionMeshes.bytes').read_bytes()).hexdigest()==base['collisionSha256']==COLLISION_SHA256,
      {'requiredSha256':COLLISION_SHA256})
for key,expected in base['metadataSha256'].items():
    # v2.8 has two narrow metadata deltas, never blanket hash exemptions.
    if key=='solidBoxes':
        ok,detail=intended_solid_box_changes(root,m)
        check('exactly_16_counter_trims_and_61_unchanged_solids',ok,detail)
    elif key=='teleports':
        ok,detail=intended_lift_control_changes(root,m)
        check('exactly_12_lift_control_relocations_only',ok,detail)
    else:
        check('unchanged_'+key,metadata_sha256(m[key])==expected)
batches=read_collision(data/'VisualMeshes.bytes')
ok,detail=protected_geometry_changes(base,batches,manifest=m,root=root,visual_path=data/'VisualMeshes.bytes')
name=('595_exact_protected_batches_and_four_exact_peer_splits'
      if m.get('features',{}).get('peer_culling_split') is True
      else '598_unchanged_protected_batches_and_one_exact_branch_revision')
check(name,ok,detail)
tri=[];names=[]
for b in batches:
    if b['group'].startswith(('Shops/','Railings/')):
        tri.extend(b['triangles']);names.extend([b['group']]*len(b['triangles']))
tri=np.asarray(tri);low=tri.min(axis=1);high=tri.max(axis=1)
tree=STRtree([box(a[0]-1e-6,a[1]-1e-6,b[0]+1e-6,b[1]+1e-6) for a,b in zip(low,high)])
hits=[];tested=0
def probe(name,footprint,zlo,zhi):
    global tested
    tested+=1;ids=tree.query(footprint);ids=ids[(high[ids,2]>=zlo)&(low[ids,2]<=zhi)]
    groups=set()
    for i in ids:
        shape=clipped_projection(tri[i:i+1],zlo,zhi)
        if shape is not None and shape.intersects(footprint):groups.add(names[i])
    if groups:hits.append({'probe':name,'groups':sorted(groups),'height':[zlo,zhi]})
for station in m['stations']:
    p=np.asarray(station['exit']);probe(station['name']+'_standing_exit',Point(p[:2]).buffer(.25,quad_segs=12),p[2]+.055,p[2]+2.2)
    p=np.asarray(station['position']);probe(station['name']+'_seated_torso',Point(p[:2]).buffer(.28,quad_segs=12),p[2]+.12,p[2]+1.10)
routes=[]
for path in m['navigationPaths']:
    routes.append((path['id'],[[*xy,path['z']] for xy in path['points']]))
try:
    ring,source=main_ring_route(m)
    check('main_ring_navigation_source',True,{'source':source,'points':len(ring),'z':float(ring[0,2])})
    routes.append(('MainRing',ring))
except (TypeError,ValueError) as error:
    check('main_ring_navigation_source',False,{'error':str(error)})
for name,points in routes:
    for i,(a,b) in enumerate(densified_segments(np.asarray(points))):
        probe(name+'_'+str(i),LineString([a[:2],b[:2]]).buffer(.25,quad_segs=8),min(a[2],b[2])+.06,max(a[2],b[2])+2.2)
check('actual_shop_and_railing_triangle_clearance',not hits,{'testedEnvelopes':tested,'hits':hits})
result={'status':'PASS' if not failures else 'FAIL','version':m['version'],'checks':checks,'failures':failures,'visualTrianglesTested':len(tri),'seconds':round(time.time()-started,2),'scope':'Designated routes: radius0.25m,height2.2m; seated torso radius0.28m,zseat+.12..1.10. Triangle surface test, not avatar simulation, hand reach, free roomscale motion or volumetric inside-only containment.'}
(root/'Docs/shop_detail_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2));raise SystemExit(bool(failures))
