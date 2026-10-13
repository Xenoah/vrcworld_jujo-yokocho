"""Independent final-payload visual/physical route regression.

Reads JYWM directly and clips actual triangles independently of other validators.
Only the explicitly named R02/R03 endpoint tread/ramp regions below 160 mm may
intersect a walking envelope. Railings and all other stair parts remain blockers.
The separate bark regression owns the full crown/legacy stair route coverage.

Usage: python Source/validate_visual_routes.py [project_root] [--report PATH]
"""
from pathlib import Path
import argparse, hashlib, json, math, struct, time
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPoint, box
from shapely.ops import unary_union

PERIMETER_TOLERANCE=.00003
HEIGHT_TOLERANCE=.00002
# Explicit coordinates are SOURCE Z-up world coordinates after altitude raising.
# No rule is based on a prefix such as Stairs/, nor on Cedar alone.
JOIN_RULES=[
 dict(id='R02_lower_150mm_step',routes=['W04'],z=140.,region=[20.6999,-12.0001,21.3001,-11.6999],
      groups=['Stairs/R02__Cedar','Ramps/R02__collision'],support_group='Ramps/R02__collision',support_offsets=[0.,.160]),
 dict(id='R03_lower_150mm_step',routes=['W05','W06'],z=146.,region=[-10.3001,21.6999,-9.9999,22.3001],
      groups=['Stairs/R03__Cedar','Ramps/R03__collision'],support_group='Ramps/R03__collision',support_offsets=[0.,.160]),
 dict(id='R02_upper_ramp_arrival',routes=['W06'],z=146.,region=[20.6999,.8999,21.3001,1.2001],
      groups=[],support_group='Ramps/R02__collision',support_offsets=[-.160,0.]),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_payload(path,scope):
    """Independent binary parser; validates finite data and exact file length."""
    batches=[]
    with path.open('rb') as stream:
        def read(n):
            data=stream.read(n)
            if len(data)!=n:raise ValueError('Truncated payload: '+str(path))
            return data
        def ints(n):return struct.unpack('<'+'I'*n,read(n*4))
        if read(4)!=b'JYWM':raise ValueError('Invalid JYWM signature')
        version,count=ints(2)
        if version!=1:raise ValueError('Unexpected JYWM version')
        for _ in range(count):
            group,material=[read(ints(1)[0]).decode() for _ in range(2)]
            nv,ni=ints(2)
            if ni%3:raise ValueError('Non-triangular payload indices')
            vertices=np.frombuffer(read(nv*12),'<f4').reshape(-1,3)
            read(nv*12) # UV float2 and RGBA byte4
            faces=np.frombuffer(read(ni*4),'<u4').reshape(-1,3)
            if not np.isfinite(vertices).all() or (ni and faces.max()>=nv):raise ValueError('Invalid mesh data')
            if not ni:continue
            triangles=vertices[faces];low=triangles.min(1);high=triangles.max(1)
            batches.append(dict(scope=scope,name=group+'__'+material,triangles=triangles,
                low=low,high=high,bounds_low=low.min(0),bounds_high=high.max(0)))
        if stream.read(1):raise ValueError('Trailing payload bytes')
    return batches


def coords(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=='Polygon':return list(geometry.exterior.coords)+[c for r in geometry.interiors for c in r.coords]
    if hasattr(geometry,'geoms'):return [c for child in geometry.geoms for c in coords(child)]
    return list(geometry.coords)


def clip_z(triangle,zlow,zhigh):
    """Sutherland-Hodgman clipping against the two horizontal body planes."""
    polygon=[np.array(v,dtype=float) for v in triangle]
    for z,side in [(zlow,1),(zhigh,-1)]:
        clipped=[]
        for v,w in zip(polygon,polygon[1:]+polygon[:1]):
            vin=side*(v[2]-z)>=-1e-9;win=side*(w[2]-z)>=-1e-9
            if vin:clipped.append(v)
            if vin!=win:clipped.append(v+(w-v)*(z-v[2])/(w[2]-v[2]))
        polygon=clipped
        if not polygon:break
    return polygon


def contact_points(triangle,footprint,zlow,zhigh):
    """Exact clipped contact vertices, retaining Z for scoped step allowances."""
    triangle=np.asarray(triangle,dtype=float)
    polygon=clip_z(triangle,zlow,zhigh)
    if not polygon:return np.empty((0,3))
    projection=MultiPoint([v[:2] for v in polygon]).convex_hull
    intersection=projection.intersection(footprint)
    if intersection.is_empty:return np.empty((0,3))
    normal=np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]);points=[]
    if abs(normal[2])>1e-10:
        for x,y in coords(intersection):
            z=triangle[0,2]-(normal[0]*(x-triangle[0,0])+normal[1]*(y-triangle[0,1]))/normal[2]
            points.append([x,y,z])
    else:
        # Vertical faces project to a line; preserve their actual vertical span.
        for v,w in zip(polygon,polygon[1:]+polygon[:1]):
            delta=w[:2]-v[:2];length2=np.dot(delta,delta)
            if length2<1e-16:
                if footprint.covers(Point(v[:2])):points.extend([v,w])
            else:
                part=LineString([v[:2],w[:2]]).intersection(footprint)
                for xy in coords(part):
                    t=np.dot(np.asarray(xy)-v[:2],delta)/length2;points.append(v+t*(w-v))
    return np.asarray(points,dtype=float).reshape(-1,3)


def permitted_step(route,group,points):
    if not len(points):return None
    for rule in JOIN_RULES:
        if route not in rule['routes'] or group not in rule['groups']:continue
        if points[:,2].min()<rule['z']-HEIGHT_TOLERANCE or points[:,2].max()>rule['z']+.160+HEIGHT_TOLERANCE:continue
        x0,y0,x1,y1=rule['region']
        if (points[:,0].min()>=x0 and points[:,0].max()<=x1 and points[:,1].min()>=y0 and points[:,1].max()<=y1):return rule['id']
    return None


SIGNS=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])
EDGES=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]


def convex_box_projection(vertices,zlow,zhigh):
    points=list(vertices[(vertices[:,2]>=zlow)&(vertices[:,2]<=zhigh)])
    for i,j in EDGES:
        a,b=vertices[i],vertices[j]
        if abs(b[2]-a[2])<1e-12:continue
        for z in [zlow,zhigh]:
            t=(z-a[2])/(b[2]-a[2])
            if 0<=t<=1:points.append(a+t*(b-a))
    return MultiPoint(np.asarray(points)[:,:2]).convex_hull if points else None


def self_checks():
    vertices=SIGNS*np.array([2.,2.,2.])+[0,0,1]
    assert convex_box_projection(vertices,.1,2.2).covers(Point(0,0).buffer(.25))
    ok=np.array([[20.9,-11.9,140.15],[21.1,-11.9,140.15]])
    assert permitted_step('W04','Stairs/R02__Cedar',ok)
    assert not permitted_step('W04','Stairs/R02__DarkTimber',ok)
    assert not permitted_step('W05','Stairs/R02__Cedar',ok)
    assert not permitted_step('W04','Safety/R02__collision',ok)
    assert not permitted_step('W04','Stairs/R02__Cedar',ok+[0,0,.02])
    assert not permitted_step('W04','Stairs/R02__Cedar',ok+[0,1,0])


def validate(root):
    started=time.time();self_checks();data=root/'Assets/TreeTopYokocho/Data'
    paths={name:data/name for name in ['WorldManifest.json','VisualMeshes.bytes','CollisionMeshes.bytes']}
    paths['layout.reference.json']=root/'Source/layout.reference.json'
    fingerprints={name:sha(path) for name,path in paths.items()}
    manifest=json.loads(paths['WorldManifest.json'].read_text());layout=json.loads(paths['layout.reference.json'].read_text())
    checks=[];failures=[];probes=[];allowed=[]
    def check(name,passed,detail=None):
        row=dict(name=name,passed=bool(passed))
        if detail is not None:row['detail']=detail
        checks.append(row)
        if not passed:failures.append(row)
    visual=read_payload(paths['VisualMeshes.bytes'],'visual');physical=read_payload(paths['CollisionMeshes.bytes'],'collision')
    batches=visual+physical;boxes=[]
    for i,record in enumerate(manifest['solidBoxes']):
        vertices=(SIGNS*np.asarray(record['size'])/2)@np.asarray(record['axes']).reshape(3,3)+record['center']
        boxes.append((record['name']+'/'+str(i),vertices))
    levels={row['level']:row['z'] for row in manifest['floors']};floor_by_z={};floor_batches=[b for b in physical if b['name'].startswith(('Floors/','Ramps/'))]
    for z in levels.values():
        parts=[]
        for batch in floor_batches:
            triangles=batch['triangles'];normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            selected=triangles[(np.max(np.abs(triangles[:,:,2]-z),axis=1)<HEIGHT_TOLERANCE)&(normals[:,2]>1e-10)]
            parts.extend(Polygon(t[:,:2]) for t in selected)
        floor_by_z[z]=unary_union(parts)
    def support(name,footprint,z):
        pieces=[floor_by_z[z]];used_rules=[]
        for rule in JOIN_RULES:
            if name not in rule['routes'] or abs(z-rule['z'])>HEIGHT_TOLERANCE:continue
            region=box(*rule['region']);lo=z+rule['support_offsets'][0];hi=z+rule['support_offsets'][1]
            for batch in floor_batches:
                if batch['name']!=rule['support_group']:continue
                triangles=batch['triangles'];normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
                indices=np.where((batch['low'][:,2]<=hi)&(batch['high'][:,2]>=lo)&(normals[:,2]>1e-10))[0]
                for i in indices:
                    clipped=clip_z(triangles[i],lo,hi)
                    if not clipped:continue
                    shape=MultiPoint(np.asarray(clipped)[:,:2]).convex_hull.intersection(region)
                    if shape.area>0:pieces.append(shape)
            used_rules.append(rule['id'])
        missing=footprint.difference(unary_union(pieces).buffer(PERIMETER_TOLERANCE)).area
        return dict(uncoveredSquareMetres=missing,perimeterToleranceMetres=PERIMETER_TOLERANCE,localRampSupportRules=used_rules)
    def probe(name,footprint,zlow,zhigh,floor_z=None):
        xy=footprint.bounds;low=np.array([xy[0],xy[1],zlow]);high=np.array([xy[2],xy[3],zhigh]);hits=[];permitted_count=0
        for batch in batches:
            if np.any(batch['bounds_low']>high) or np.any(batch['bounds_high']<low):continue
            ids=np.where(np.all(batch['low']<=high,axis=1)&np.all(batch['high']>=low,axis=1))[0]
            for i in ids:
                points=contact_points(batch['triangles'][i],footprint,zlow,zhigh)
                if not len(points):continue
                bounds=[points.min(0).tolist(),points.max(0).tolist()]
                permit=permitted_step(name,batch['name'],points)
                if permit:
                    allowed.append(dict(probe=name,rule=permit,scope=batch['scope'],group=batch['name'],triangle=int(i),contactBounds=bounds));permitted_count+=1
                else:
                    hits.append(dict(scope=batch['scope'],group=batch['name'],triangle=int(i),contactBounds=bounds));break
        for name_box,vertices in boxes:
            if np.any(vertices.min(0)>high) or np.any(vertices.max(0)<low):continue
            shape=convex_box_projection(vertices,zlow,zhigh)
            if shape is not None and shape.intersects(footprint):hits.append(dict(scope='convex_BoxCollider_volume',group=name_box))
        row=dict(name=name,z=[zlow,zhigh],hits=hits,permittedStepContacts=permitted_count)
        supported=True
        if floor_z is not None:
            row['support']=support(name,footprint,floor_z);supported=row['support']['uncoveredSquareMetres']<1e-7
        probes.append(row);check(name+'_clear_and_supported',not hits and supported,row)
    # All49 guest records, without broad exclusions for their shop furniture.
    for seat in manifest['stations']:
        point=np.asarray(seat['position']);exit=np.asarray(seat['exit']);z=point[2]-.7
        probe(seat['name']+'/seated',Point(point[:2]).buffer(.28,quad_segs=32),point[2]+.12,point[2]+1.10)
        probe(seat['name']+'/exit',Point(exit[:2]).buffer(.25,quad_segs=32),z+.055,z+2.2,z)
        probe(seat['name']+'/transfer',LineString([point[:2],exit[:2]]).buffer(.25,quad_segs=32),z+.76,z+1.95)
    navigation=list(manifest.get('navigationPaths',[]))
    if isinstance(manifest.get('mainRingNavigation'),dict):navigation.append(manifest['mainRingNavigation'])
    names=[r['id'] for r in navigation]
    check('all_seven_audited_level_routes_present',set(['W01','W02','W03','W04','W05','W06','MainRing']).issubset(names) and len(names)==len(set(names)),names)
    for route in navigation:
        points=np.asarray(route['points'],dtype=float);valid=points.ndim==2 and points.shape[1]==2 and len(points)>=2 and np.isfinite(points).all()
        check(route['id']+'_valid_manifest_route',valid)
        if valid:
            shape=LineString(points).buffer(.25,quad_segs=32);z=route['z'];probe(route['id'],shape,z+.055,z+2.2,z)
    plans={r['shop']:r.get('staffEntry') for r in manifest['shopCraft']}
    check('eight_staff_entry_routes_present',len(plans)==8 and all(plans.values()))
    for shop in layout['shops']:
        plan=plans.get(shop['id'])
        if not plan:continue
        angle=math.radians(shop['front_deg']);front=np.array([math.cos(angle),math.sin(angle)]);right=np.array([front[1],-front[0]])
        points=[np.array([shop['x'],shop['y']])+right*x+front*y for x,y in plan['centerline']]
        z=levels[shop['level']];probe(shop['id']+'/staff_r325_h220',LineString(points).buffer(.325,quad_segs=64),z+.055,z+2.2,z)
    for control in manifest['teleports']:
        x,y,zz=control['destination'];z=min(levels.values(),key=lambda h:abs(h-zz))
        probe(control['name']+'/destination',Point(x,y).buffer(.325,quad_segs=64),z+.055,z+2.2,z)
        px,py,pz=control['position'];source_z=min(levels.values(),key=lambda h:abs(h-(pz-1.25)))
        approach_x=px+.60
        points=[[x,y],[approach_x,y],[approach_x,py]]
        probe(control['name']+'/control_approach',LineString(points).buffer(.325,quad_segs=64),source_z+.055,source_z+2.2,source_z)
    for i,spawn in enumerate(manifest['spawns']):
        x,y,zz=spawn['position'];z=min(levels.values(),key=lambda h:abs(h-zz))
        probe('Spawn/'+str(i),Point(x,y).buffer(.25,quad_segs=32),z+.055,z+2.2,z)
    check('input_snapshot_unchanged',fingerprints=={name:sha(path) for name,path in paths.items()})
    return dict(version=manifest['version'],status='PASS' if not failures else 'FAIL',checks=checks,failures=failures,
        probes=probes,permittedStepContacts=allowed,localizedJoinRules=JOIN_RULES,inputSha256=fingerprints,
        visualBatches=len(visual),physicalBatches=len(physical),convexBoxes=len(boxes),seconds=round(time.time()-started,2),
        scope='Actual exported visual/collision triangles, complete convex BoxCollider volumes and continuous floor/ramp support. Guest torso/exit/transfer, eight staff routes, seven manifest level routes, lift destinations/control approaches and spawns. Only named local R02/R03 tread/ramp contacts up to160mm are permitted. Supporting-bark crown/stair coverage is a separate regression. Not Unity/VRChat, roomscale, avatar simulation or general closed-visual-mesh inside-only containment.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',nargs='?',type=Path,default=Path(__file__).resolve().parent.parent);parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=validate(args.root);destination=args.report or args.root/'Docs/visual_route_validation.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],version=result['version'],probes=len(result['probes']),failures=result['failures'],permittedStepContacts=len(result['permittedStepContacts']),seconds=result['seconds'],report=str(destination)),indent=2))
    return bool(result['failures'])

if __name__=='__main__':raise SystemExit(main())
