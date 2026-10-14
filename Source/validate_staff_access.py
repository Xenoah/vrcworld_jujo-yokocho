"""Actual exported staff-entry/service-aisle visual, collider and floor checks.

Uses explicitly authored shop-local routes. This is an offline swept-prism test,
not Unity CharacterController simulation or a whole-shop accessibility claim.
"""
from pathlib import Path
import hashlib,json,math,sys,time
import numpy as np
from shapely import wkt
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union
from validate_crown import read_collision,clipped_projection,box_triangles,Rays


def intended_counter_changes(root,manifest):
    """Allow exactly the two physical counter trims per shop, nothing else."""
    from staff_access import COUNTER_TRIM,staff_entry_plan
    before=json.loads((root/'Docs/baselines/verified_shop_solids_2.7.0.json').read_text())['solidBoxes']
    after=manifest['solidBoxes']
    layout=json.loads((root/'Source/layout.reference.json').read_text())['shops']
    if len(before)!=77 or len(after)!=len(before):return False,{'reason':'solid count changed'}
    expected_indices={9*i+j for i in range(8) for j in (7,8)}
    changed=[];errors=[]
    for i,(old,new) in enumerate(zip(before,after)):
        if i not in expected_indices:
            if old!=new:errors.append({'index':i,'reason':'unrelated solid changed'})
            continue
        shop=layout[i//9];plan=staff_entry_plan(i//9,shop['width'],shop['depth'])
        shift=-plan['side']*COUNTER_TRIM/2
        center=np.asarray(old['center'])+np.asarray(old['axes'][:3])*shift
        size=np.asarray(old['size'])-[COUNTER_TRIM,0,0]
        good=(set(old)==set(new) and old['name']==new['name']==shop['id']+'_solid' and old['axes']==new['axes']
              and np.allclose(new['center'],center,rtol=0,atol=1e-9)
              and np.allclose(new['size'],size,rtol=0,atol=1e-9))
        if not good:errors.append({'index':i,'reason':'counter trim differs from authored side/amount'})
        changed.append({'index':i,'shop':shop['id'],'side':plan['side'],'trim':COUNTER_TRIM})
    return not errors,{'counterBoxes':changed,'unchangedOtherBoxes':len(before)-16,'errors':errors}


def main(root):
    started=time.time();data=root/'Assets/TreeTopYokocho/Data'
    m=json.loads((data/'WorldManifest.json').read_text())
    if m.get('features',{}).get('shop_personality') is True:
        from validate_shop_personality_access import validate
        result=validate(root)
        (root/'Docs/staff_access_validation.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('checks','probes','diagnostics','connection')},indent=2))
        return result['status']!='PASS'
    layout=json.loads((root/'Source/layout.reference.json').read_text())['shops']
    levels={x['level']:x for x in m['floors']}
    plans={x['shop']:x['staffEntry'] for x in m['shopCraft']}
    checks=[];failures=[];routes=[]
    def check(name,ok,detail=None):
        row={'name':name,'passed':bool(ok)}
        if detail is not None:row['detail']=detail
        checks.append(row)
        if not ok:failures.append(row)
    ok,details=intended_counter_changes(root,m)
    check('exactly_16_intended_counter_collider_trims',ok,details)
    visual=read_collision(data/'VisualMeshes.bytes')
    physical=read_collision(data/'CollisionMeshes.bytes')
    floor_triangles=np.concatenate([b['triangles'] for b in physical if b['group'].startswith(('Floors/','Ramps/'))])
    rays=Rays(floor_triangles)
    floor_normals=np.cross(floor_triangles[:,1]-floor_triangles[:,0],floor_triangles[:,2]-floor_triangles[:,0])
    actual_floors={}
    for level in levels.values():
        selected=floor_triangles[(np.max(np.abs(floor_triangles[:,:,2]-level['z']),axis=1)<2e-5)&(floor_normals[:,2]>1e-12)]
        actual_floors[level['level']]=unary_union([Polygon(t[:,:2]) for t in selected])
    records=[]
    for scope,batches in [('visual',visual),('collision',physical)]:
        for b in batches:
            t=b['triangles']
            records.append((scope,b['group'],t,t.min((0,1)),t.max((0,1))))
    for i,b in enumerate(m['solidBoxes']):
        t=box_triangles(b)
        records.append(('collision','SolidBox/'+b['name']+'/'+str(i),t,t.min((0,1)),t.max((0,1))))
    def intersections(shape,zlo,zhi):
        x0,y0,x1,y1=shape.bounds;hits={}
        for scope,name,t,lo,hi in records:
            if hi[0]<x0 or lo[0]>x1 or hi[1]<y0 or lo[1]>y1 or hi[2]<zlo or lo[2]>zhi:continue
            a=t.min(1);b=t.max(1)
            candidates=t[(a[:,0]<=x1)&(b[:,0]>=x0)&(a[:,1]<=y1)&(b[:,1]>=y0)&(a[:,2]<=zhi)&(b[:,2]>=zlo)]
            for triangle in candidates:
                p=clipped_projection(triangle[None],zlo,zhi)
                if p is not None and p.intersects(shape):
                    hits.setdefault(scope,set()).add(name);break
        return {key:sorted(value) for key,value in hits.items()}
    support_count=0
    for shop in layout:
        plan=plans[shop['id']];angle=math.radians(shop['front_deg'])
        front=np.array([math.cos(angle),math.sin(angle)]);right=np.array([front[1],-front[0]])
        points=[np.array([shop['x'],shop['y']])+right*p[0]+front*p[1] for p in plan['centerline']]
        line=LineString(points);floor=levels[shop['level']];z=floor['z'];footprint=wkt.loads(floor['wkt'])
        missing=line.buffer(.325,quad_segs=32).difference(footprint).area
        check(shop['id']+'_full_width_floor_containment',missing<1e-7,{'missingSquareMetres':missing})
        missing=line.buffer(.325,quad_segs=32).difference(actual_floors[shop['level']].buffer(3e-5)).area
        check(shop['id']+'_continuous_exported_floor_support',missing<1e-7,{'missingSquareMetres':missing,'perimeterToleranceMetres':3e-5})
        for radius in (.25,.325):
            shape=line.buffer(radius,quad_segs=32)
            for height in (1.8,2.2):
                hits=intersections(shape,z+.055,z+height)
                check(shop['id']+f'_r{radius}_h{height}',not hits,hits)
        misses=[]
        for distance in np.linspace(0,line.length,max(2,math.ceil(line.length/.2)+1)):
            center=np.asarray(line.interpolate(distance).coords[0])
            offsets=[[0,0]]+[[.325*math.cos(a),.325*math.sin(a)] for a in np.linspace(0,math.tau,8,endpoint=False)]
            for offset in offsets:
                xy=center+offset;support_count+=1
                hit=rays.hit([*xy,z+.5],[0,0,-1],.65)
                if hit is None or abs(hit-.5)>2e-5:misses.append({'xy':xy.tolist(),'distance':hit})
        check(shop['id']+'_actual_floor_rays',not misses,{'misses':misses[:12]})
        routes.append({'shop':shop['id'],'side':plan['side'],'length':line.length,'worldCenterline':[[*xy,z] for xy in points]})
    base=json.loads((root/'Docs/baselines/verified_layout_2.6.0.json').read_text())
    check('unchanged_floor_and_fall_barrier_meshes',hashlib.sha256((data/'CollisionMeshes.bytes').read_bytes()).hexdigest()==base['collisionSha256'])
    result={'status':'PASS' if not failures else 'FAIL','version':m['version'],'checks':checks,'failures':failures,
            'routes':routes,'sweptEnvelopes':32,'supportProbes':support_count,'seconds':round(time.time()-started,2),
            'scope':'Actual exported visual/collision triangles and 77 explicit box colliders. Eight entrance plus short service-aisle routes, test radii .25/.325m, heights1.8/2.2m. Floor support and geometric source checks only; not whole-room, inside-only volume containment, Unity/VRChat simulation or an accessibility certification.'}
    (root/'Docs/staff_access_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2));return bool(failures)


if __name__=='__main__':
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent))
