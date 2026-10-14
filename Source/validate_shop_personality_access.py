"""Actual redesigned-shop stations/routes versus final visual and collider data.

Transfer is a conservative authored continuous-clearance design guarantee,
not a claim about the VRC station exit trajectory (which may teleport).
No old furniture or shop prefix is excluded. Requires continuous physical floor
support and checks full convex collider volume, not just box surfaces. Larger
radius diagnostics are reported separately, not silently called accessible.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
from shapely.geometry import LineString,Point,Polygon,MultiPoint
from shapely.ops import unary_union




def inflated_obstacle_union(pieces,radius):
    """Buffer every obstacle before union, including line/point projections.

    Minkowski dilation distributes over set union. Buffer-first avoids GEOS
    failure on nearly coincident mixed-dimensional clipped craft surfaces.
    This is numerical/tessellation equivalence, not bitwise polygon identity.
    No projection is skipped, repaired with buffer(0), or reduced in radius.
    """
    inflated=[]
    for piece in pieces:
        value=piece.buffer(radius,quad_segs=32)
        if not piece.is_empty and (value.is_empty or not value.is_valid or not value.covers(piece)):
            raise ValueError('Obstacle inflation lost a projection or produced invalid geometry')
        inflated.append(value)
    result=unary_union(inflated)
    if not result.is_valid:raise ValueError('Inflated obstacle union is invalid')
    return result

def seat_datum_diagnostic(station,visual):
    """Report a candidate support surface; no new anthropometric pass threshold.

    Cast at the actual station centre onto near-horizontal upward triangles
    within -0.20/+0.10 m of the station datum. Highest such surface is reported.
    This is mesh evidence, not a claim about cushion compression or VRC pose.
    """
    p=np.asarray(station['position'],float);sid=station['name'].split('_')[0];candidates=[]
    for batch in visual:
        if not batch['name'].startswith('Shops/'+sid+'/Personality/'):continue
        if np.any(p[:2]<batch['bounds_low'][:2]-1e-6) or np.any(p[:2]>batch['bounds_high'][:2]+1e-6):continue
        ids=np.where(np.all(batch['low'][:,:2]<=p[:2]+1e-6,axis=1)&np.all(batch['high'][:,:2]>=p[:2]-1e-6,axis=1))[0]
        for i in ids:
            tri=batch['triangles'][i];a,b,c=tri;normal=np.cross(b-a,c-a);length=np.linalg.norm(normal)
            if length<1e-12 or normal[2]/length<.9:continue
            matrix=np.column_stack((b[:2]-a[:2],c[:2]-a[:2]))
            if abs(np.linalg.det(matrix))<1e-12:continue
            uv=np.linalg.solve(matrix,p[:2]-a[:2])
            if min(uv)<-1e-5 or sum(uv)>1+1e-5:continue
            z=float(a[2]+uv[0]*(b[2]-a[2])+uv[1]*(c[2]-a[2]))
            if p[2]-.20<=z<=p[2]+.10:candidates.append(dict(surfaceZ=z,group=batch['name'],triangle=int(i),upwardNormalZ=float(normal[2]/length)))
    support=max(candidates,key=lambda r:r['surfaceZ']) if candidates else None
    return dict(station=station['name'],stationZ=float(p[2]),candidateSeatSupport=support,
                stationMinusSurfaceMetres=None if support is None else round(float(p[2]-support['surfaceZ']),6),
                diagnosticOnly=True,scope='Station-centre near-horizontal upward visual surface; no new height or pose acceptance threshold.')

def validate(root,*,proposal=False):
    from validate_visual_routes import read_payload,contact_points,convex_box_projection,SIGNS,clip_z,HEIGHT_TOLERANCE,PERIMETER_TOLERANCE
    import shop_personality_contract as contract
    started=time.time();data=root/'Assets/TreeTopYokocho/Data';paths={n:data/n for n in ('WorldManifest.json','VisualMeshes.bytes','CollisionMeshes.bytes')}
    fingerprints={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()};m=json.loads(paths['WorldManifest.json'].read_text());before=contract.load_before()
    checks=[];failures=[];diagnostics=[];probes=[]
    def check(name,passed,detail=None):
        row=dict(name=name,passed=bool(passed))
        if detail is not None:row['detail']=detail
        checks.append(row)
        if not passed:failures.append(row)
    import rpg_identity_contract as rpg
    if rpg.requested(m):
        if proposal:
            from peer_culling_contract import read_visual
            rows=rpg.summarize_batches(read_visual(paths['VisualMeshes.bytes']))
            ok,metadata=rpg.audit_scope(rows,m)
            from rpg_runtime_compatibility import verify_runtime
            try:verify_runtime(root)
            except (ValueError,OSError,KeyError,TypeError) as exc:
                ok=False;metadata['errors'].append(dict(reason=str(exc)))
            metadata['proposalOnly']=True
            metadata['scope']='Current payload scope authentication for geometry diagnostics only; no frozen art approval.'
            if fingerprints['CollisionMeshes.bytes']!=rpg.load_before()['collisionSha256']:
                ok=False;metadata['errors'].append(dict(reason='Immutable collision bytes changed'))
        else:
            ok,metadata=rpg.validate_native(root,m)
        if ok:
            old_ok,prior=contract.audit_metadata(rpg.load_before()['manifest'],before=before)
            metadata['priorMetadataScope']=prior
            if not old_ok:metadata['errors'].extend(prior['errors'])
            ok=ok and old_ok
    else:ok,metadata=contract.audit_metadata(m,before=before)
    check('explicit_local_world_metadata_scope',ok,metadata)
    if not ok and any(e['reason']!='Unrelated manifest field changed' for e in metadata['errors']):return dict(status='FAIL',checks=checks,failures=failures,probes=[],diagnostics=[],seconds=round(time.time()-started,2))
    visual=read_payload(paths['VisualMeshes.bytes'],'visual');physical=read_payload(paths['CollisionMeshes.bytes'],'collision');batches=visual+physical;boxes=[]
    for i,r in enumerate(m['solidBoxes']):
        vertices=(SIGNS*np.asarray(r['size'])/2)@np.asarray(r['axes']).reshape(3,3)+r['center'];boxes.append((r['name']+'/'+str(i),vertices))
    floors={}
    for z in {s['frame']['floorZ'] for s in m['shopPersonality']['shops']}:
        parts=[]
        for batch in physical:
            if not batch['name'].startswith(('Floors/','Ramps/')):continue
            t=batch['triangles'];normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);selected=t[(np.max(np.abs(t[:,:,2]-z),axis=1)<HEIGHT_TOLERANCE)&(normal[:,2]>1e-10)]
            parts.extend(Polygon(p[:,:2]) for p in selected)
        floors[z]=unary_union(parts)
    def intersections(foot,zlo,zhi,collect_polygons=False):
        xy=foot.bounds;lo=np.array([xy[0],xy[1],zlo]);hi=np.array([xy[2],xy[3],zhi]);hits=[];pieces=[]
        for batch in batches:
            if np.any(batch['bounds_low']>hi) or np.any(batch['bounds_high']<lo):continue
            ids=np.where(np.all(batch['low']<=hi,axis=1)&np.all(batch['high']>=lo,axis=1))[0]
            for i in ids:
                t=batch['triangles'][i]
                if collect_polygons:
                    p=clip_z(t,zlo,zhi)
                    if not p:continue
                    shape=MultiPoint(np.asarray(p)[:,:2]).convex_hull.intersection(foot)
                    if not shape.is_empty:pieces.append(shape)
                else:
                    if len(contact_points(t,foot,zlo,zhi)):
                        hits.append(dict(scope=batch['scope'],group=batch['name'],triangle=int(i)));break
        for name,vertices in boxes:
            if np.any(vertices.min(0)>hi) or np.any(vertices.max(0)<lo):continue
            shape=convex_box_projection(vertices,zlo,zhi)
            if shape is not None and shape.intersects(foot):
                if collect_polygons:pieces.append(shape.intersection(foot))
                else:hits.append(dict(scope='convex_BoxCollider_volume',group=name))
        return pieces if collect_polygons else hits
    def probe(name,foot,zlo,zhi,floor=None,diagnostic=False):
        hits=intersections(foot,zlo,zhi);missing=None
        if floor is not None:missing=foot.difference(floors[floor].buffer(PERIMETER_TOLERANCE)).area
        row=dict(name=name,z=[zlo,zhi],hits=hits,uncoveredFloorSquareMetres=missing,passed=not hits and (missing is None or missing<1e-7))
        if diagnostic:diagnostics.append(row)
        else:probes.append(row);check(name,row['passed'],row)
    layout={s['id']:s for s in before['layout']};connection=[];seat_datums=[]
    for shop in m['shopPersonality']['shops']:
        sid=shop['id'];z=shop['frame']['floorZ'];world=shop['world'];stations=world['stations'];routes=world['routes']
        is_entry=lambda r:r.get('role')=='entrance' or 'entrance' in r['name'].lower() or 'entry' in r['name'].lower()
        is_service=lambda r:r.get('role') in ('staff','service') or 'staff' in r['name'].lower() or 'service' in r['name'].lower()
        check(sid+'_required_named_access',any(is_entry(r) for r in routes) and any(is_service(r) for r in routes),[r['name'] for r in routes])
        for station in stations:
            p=np.asarray(station['position']);e=np.asarray(station['exit']);name=station['name']
            seat_datums.append(seat_datum_diagnostic(station,visual))
            probe(name+'/seated_torso',Point(p[:2]).buffer(.28,quad_segs=32),p[2]+.12,p[2]+1.10)
            probe(name+'/standing_exit',Point(e[:2]).buffer(.25,quad_segs=32),z+.055,z+2.2,z)
            probe(name+'/seat_to_exit_transfer',LineString([p[:2],e[:2]]).buffer(.25,quad_segs=32),p[2]+.06,max(p[2]+1.10,z+1.95))
            probe(name+'/larger_exit_r325',Point(e[:2]).buffer(.325,quad_segs=32),z+.055,z+2.2,z,True)
        for route in routes:
            points=np.asarray(route['points'],float);valid=points.ndim==2 and points.shape[1]==3 and len(points)>=2 and np.isfinite(points).all()
            check(sid+'/'+route['name']+'/finite_route',valid)
            if not valid:continue
            line=LineString(points[:,:2]);probe(sid+'/'+route['name']+'/r250_h220',line.buffer(.25,quad_segs=32),z+.055,z+2.2,z)
            probe(sid+'/'+route['name']+'/r325_h220',line.buffer(.325,quad_segs=32),z+.055,z+2.2,z,not(is_entry(route) or is_service(route)))
        # Independent free-space component proof within each complete shop and
        # front approach. Inflation includes visual triangles and box volumes.
        frame=shop['frame'];o=np.asarray(frame['origin']);right=np.asarray(frame['right']);front=np.asarray(frame['front']);w=layout[sid]['width'];dep=layout[sid]['depth']
        corners=[(o+right*x+front*y)[:2] for x,y in [(-w/2-.8,-dep/2-.8),(w/2+.8,-dep/2-.8),(w/2+.8,dep/2+2.2),(-w/2-.8,dep/2+2.2)]];region=Polygon(corners)
        obstacle_pieces=intersections(region,z+.055,z+2.2,True);inflated_obstacles=inflated_obstacle_union(obstacle_pieces,.25);free=floors[z].intersection(region).buffer(-.25).difference(inflated_obstacles)
        components=[free] if free.geom_type=='Polygon' else [p for p in getattr(free,'geoms',[]) if p.geom_type=='Polygon']
        def memberships(xy):return [i for i,p in enumerate(components) if p.buffer(1e-7).covers(Point(xy))]
        entrances=[r for r in routes if is_entry(r)];anchors=[p for r in entrances for p in (r['points'][0],r['points'][-1])]
        anchor_sets=[set(memberships(p[:2])) for p in anchors];reachable=set.union(*anchor_sets) if anchor_sets else set()
        by_seat={s['name']:memberships(s['exit'][:2]) for s in stations};bad=[name for name,values in by_seat.items() if not set(values)&reachable]
        row=dict(shop=sid,radius=.25,obstacleProjectionCount=len(obstacle_pieces),inflationRule='Every polygon/line/point buffered at full radius before union, quad_segs32',components=len(components),entranceComponents=sorted(reachable),seatExitComponents=by_seat,disconnectedSeats=bad)
        connection.append(row);check(sid+'_all_seat_exits_connect_to_authored_entrance',not bad and bool(reachable),row)
    check('physical_floors_ramps_and_fall_barriers_unchanged',fingerprints['CollisionMeshes.bytes']==before['collisionSha256'])
    check('input_snapshot_unchanged',fingerprints=={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()})
    return dict(status='FAIL' if failures else 'PASS',proposalOnly=proposal,version=m['version'],checks=checks,failures=failures,probes=probes,diagnostics=diagnostics,connection=connection,seatDatumDiagnostics=seat_datums,
                actualStationCount=len(m['stations']),actualSolidBoxes=len(m['solidBoxes']),requiredGuestRadius=.25,requiredEntranceStaffServiceRadius=.325,diagnosticCustomerRadius=.325,inputSha256=fingerprints,seconds=round(time.time()-started,2),
                scope='Actual final visual/collision triangles and complete convex box volumes. 49 seated torsos/exits/transfers; all named local shop routes; continuous floor support; radius .25 entrance/exit free-space components. Entrance/staff/service routes require .325 m; .325 m customer/seat-exit envelopes are diagnostic. No blanket shop exclusions. The transfer sweep is a conservative design envelope, not a simulated/observed VRC exit trajectory. No Unity/VRChat, roomscale, hand reach, arbitrary avatar, inside-only visual solid containment or accessibility certification.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--report',type=Path,required=True);parser.add_argument('--proposal',action='store_true',help='Scope-checked current geometry diagnostics without art admission');args=parser.parse_args();sys.path.append(str(args.root/'Source'));result=validate(args.root,proposal=args.proposal)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','probes','diagnostics','connection','seatDatumDiagnostics')},ensure_ascii=False,indent=2));return result['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
