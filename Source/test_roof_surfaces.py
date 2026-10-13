"""Small, deterministic roof/drainage checks against pinned v2.8 lower surfaces.
No old source module or full-world fixture is required at test time.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import trimesh
from world_geometry import Geometry
import high_detail,timber_craft

BASELINE_SHA256='4a60cff30ef53ef525275add69709870e9ca775da9838dc08665242ca5e39599'

def fixture(shop,staff=False,high=high_detail,timber=timber_craft,geometry=Geometry):
    g=geometry();g.group='Shops/'+shop['id']
    m=dict(dark='DarkTimber',wood='Cedar',iron='Iron',trim='Bronze',stone='Stone')
    for material in ['Kawara',*m.values()]:g.material(material,(.5,.4,.3),normal='test_normal.png')
    P=lambda x,y,z:np.array([x,y,z],float)
    B=lambda x,y,z,w,d,h,mat:g.box(P(x,y,z),(w,d,h),mat)
    high.roof_tiles(g,P,shop['width'],shop['depth'],'Kawara','DarkTimber')
    timber.add_shop_joinery(g,P,B,shop['width'],shop['depth'],int(shop['id'][1:])-1,m,staff_entry=staff)
    return g

def low_fingerprint(g):
    records=[]
    for (_,material),b in g.batches.items():
        vertices=np.asarray(b['v'])
        for face in b['f']:
            tri=vertices[face]
            if tri[:,2].min()>=2.60-1e-8:continue
            # Cyclic rotations only preserve oriented winding and multiplicity.
            tri=np.round(tri,8);tri[tri==0]=0
            coords=min(tuple(np.roll(tri,k,axis=0).flat) for k in range(3))
            records.append((material,coords))
    raw=json.dumps(sorted(records),separators=(',',':')).encode()
    return dict(triangles=len(records),sha256=hashlib.sha256(raw).hexdigest())

def run(root):
    path=root/'Docs/baselines/verified_roof_surfaces_2.8.0.json';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASELINE_SHA256:raise AssertionError('Pinned roof baseline changed')
    base=json.loads(raw);layout=json.loads((root/'Source/layout.reference.json').read_text())['shops'];rows=[]
    for staff in [False,True]:
        for shop in layout:
            g=fixture(shop,staff);old=base['shops'][shop['id']+('/staff' if staff else '/closed')]
            assert low_fingerprint(g)==old['below_2_60m'],shop['id']+' lower assembly changed'
            v=np.concatenate([np.asarray(b['v']) for b in g.batches.values()])
            assert (v.min(0)>=np.array(old['bounds'][0])-1e-7).all()
            assert (v.max(0)<=np.array(old['bounds'][1])+1e-7).all()
            g.compact();g.repair_normal_uvs();g.bake_mood([])
            triangles=0
            for (_,material),b in g.batches.items():
                assert np.isfinite(b['v']).all() and np.isfinite(b['uv']).all()
                q=b['v'][b['f']];area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
                assert (area>1e-10).all(),material+' degenerate geometry'
                u=b['uv'][b['f']];a=u[:,1]-u[:,0];c=u[:,2]-u[:,0]
                assert (abs(a[:,0]*c[:,1]-a[:,1]*c[:,0])>1e-10).all(),material+' collapsed tangent'
                assert len(b['colors'])==len(b['v'])
                triangles+=len(b['f'])
            rows.append(dict(shop=shop['id'],staff_entry=staff,triangles=triangles,lower_triangles=old['below_2_60m']['triangles'],bounds_contained=True))
    for angle in [0,.7,2.1]:
        c,s=np.cos(angle),np.sin(angle);P=lambda x,y,z:np.array([x*c-y*s,x*s+y*c,z])
        for component in ['channel','stop']:
            g=Geometry()
            if component=='channel':timber_craft._half_round_channel(g,P,-1,1,0,2.77,2.758,.05,.004,'Test')
            else:timber_craft._gutter_end_stop(g,P,0,.004,0,2.77,.05,'Test')
            b=next(iter(g.batches.values()));mesh=trimesh.Trimesh(b['v'],b['f'],process=True)
            assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,component
    return dict(status='PASS',fixtures=rows,gutter_rotations=3,scope='Generated small roof and joinery fixtures, unchanged lower geometry and bounds, surface/tangent finiteness, closed thin-shell winding. No Unity execution.')

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
    result=run(root);(root/'Docs/roof_surface_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
