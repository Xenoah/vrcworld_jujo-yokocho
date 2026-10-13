"""Run without importing build_world or regenerating the world.

Usage: PYTHONDONTWRITEBYTECODE=1 tree-venv/bin/python /tmp/yokocho-next-deck/test_deck_surface.py
"""
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon, Point, LineString, box
from shapely.ops import unary_union
ROOT=next(p for p in [Path(os.environ.get('YOKOCHO_ROOT','.')),
                         Path(__file__).resolve().parent.parent,Path.cwd(),Path.cwd()/'tree-work']
          if (p/'Assets/TreeTopYokocho/Data/WorldManifest.json').exists())
sys.path[:0]=[str(Path(__file__).parent),str(ROOT/'Source')]
from world_geometry import Geometry,poly_mesh
from high_detail import detailed_deck
from deck_surface import add_deck_surface,GROOVE_DEPTH,SLAB_THICKNESS,SCAN_U


def geometry():
    g=Geometry()
    manifest=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    for material in manifest['materials']:
        if material['name'] in ('Cedar','DarkTimber','Iron','Bronze','Grout'):
            g.materials[material['name']]=material
    return g
M={'wood':'Cedar','dark':'DarkTimber','iron':'Iron','trim':'Bronze'}


def old_deck(g,poly,z):
    v,f=poly_mesh(poly,z,.3);g.add(v,f,'Cedar',v[:,:2])
    detailed_deck(g,poly,z,'Cedar','Grout')
    lo=poly.bounds
    for x in np.arange(math.floor(lo[0]*4)/4,lo[2],.28):
        line=LineString([(x,lo[1]-1),(x,lo[3]+1)]).intersection(poly)
        for ln in (list(line.geoms) if line.geom_type=='MultiLineString' else [line]):
            if ln.geom_type!='LineString' or ln.length<.03:continue
            a,b=list(ln.coords)[0],list(ln.coords)[-1]
            g.quad([(a[0]-.006,a[1],z+.002),(b[0]-.006,b[1],z+.002),
                    (b[0]+.006,b[1],z+.002),(a[0]+.006,a[1],z+.002)],'Grout')
    return sum(len(b['f']) for b in g.batches.values())


def digest(g):
    h=hashlib.sha256()
    h.update(json.dumps(g.materials,sort_keys=True).encode())
    for key,b in sorted(g.batches.items()):
        h.update(str(key).encode())
        for field in ['v','f','uv']:
            h.update(np.asarray(b[field]).tobytes())
    return h.hexdigest()


def inspect(g,poly,z,check_overlap=True):
    projected=[];bed=[];outer_fail=0;max_height=-math.inf;min_height=math.inf
    triangles=0;uv_min=math.inf;degenerates=[];flat_area=0.
    boundary=poly.buffer(1e-8)
    plank_uv=[]
    for (group,mat),b in g.batches.items():
        v=np.asarray(b['v']);uv=np.asarray(b['uv']);f=np.asarray(b['f'])
        assert np.isfinite(v).all() and np.isfinite(uv).all(),(group,mat,'not finite')
        assert f.min()>=0 and f.max()<len(v)
        max_height=max(max_height,v[:,2].max());min_height=min(min_height,v[:,2].min())
        assert all(boundary.covers(Point(x,y)) for x,y in v[:,:2]),(group,'escaped footprint')
        q=v[f];e1=q[:,1]-q[:,0];e2=q[:,2]-q[:,0];cross=np.cross(e1,e2)
        area=np.linalg.norm(cross,axis=1)*.5
        assert (area>1e-15).all(),(group,'zero area',area.min())
        # Exercise the final raised-world float32 precision as well as source mesh.
        export_v=v.copy()
        if z>=33:export_v[:,2]+=100
        f32=export_v.astype(np.float32).astype(float)[f]
        area32=np.linalg.norm(np.cross(f32[:,1]-f32[:,0],f32[:,2]-f32[:,0]),axis=1)*.5
        if (area32<=1e-14).any():degenerates.append((group,mat,int((area32<=1e-14).sum())))
        quv=uv[f];a=quv[:,1]-quv[:,0];buv=quv[:,2]-quv[:,0]
        ua=np.abs(a[:,0]*buv[:,1]-a[:,1]*buv[:,0])
        uv_min=min(uv_min,ua.min())
        assert (ua>1e-15).all(),(group,mat,'collapsed tangent',ua.min())
        triangles+=len(f)
        for p,n in zip(q,cross):
            if group.endswith('/Planks'):
                assert n[2]>0,(group,'reversed top/bevel winding',n)
                if check_overlap:projected.append(Polygon(p[:,:2]))
                if np.max(np.abs(p[:,2]-z))<1e-10:flat_area+=n[2]*.5
            elif n[2]>1e-14:
                assert np.max(np.abs(p[:,2]-(z-GROOVE_DEPTH)))<1e-10,'incorrect bed top winding'
                bed.append(Polygon(p[:,:2]))
            elif n[2]<-1e-14:
                assert np.max(np.abs(p[:,2]-(z-SLAB_THICKNESS)))<1e-10,'incorrect bed bottom winding'
            else:
                outward=n[:2]/np.linalg.norm(n[:2]);mid=p[:,:2].mean(axis=0)
                assert not poly.contains(Point(*(mid+outward*.00001))),'reversed slab/hole wall winding'
        if group.endswith('/Planks') and mat!='DeckForgedNail':
            plank_uv.append(uv)
            assert uv[:,1].min()>=.0449 and uv[:,1].max()<=.7351,(mat,'screw-row crop leak',uv[:,1].min(),uv[:,1].max())
            assert all(any(a-1e-8<=u<=b+1e-8 for a,b in SCAN_U) for u in uv[:,0]),'painted seam crop leak'
    # Complete projected coverage is supplied by the uninterrupted groove bed.
    coverage=unary_union(bed)
    coverage_error=poly.symmetric_difference(coverage).area
    assert coverage_error<max(1e-9,poly.area*1e-11),('footprint/holes changed',coverage_error)
    assert abs(max_height-z)<1e-12 and abs(min_height-(z-.3))<1e-12,(min_height,max_height,z)
    overlap_error=None
    if check_overlap:
        covered=unary_union(projected)
        overlap_error=sum(p.area for p in projected)-covered.area
        assert overlap_error<max(1e-8,poly.area*1e-10),('overlapping plank surfaces',overlap_error)
    return {'triangles':triangles,'footprintCoverageError':coverage_error,
            'plankOverlapArea':overlap_error,'flatTopFraction':flat_area/poly.area,
            'minimumUvDeterminant':uv_min,'float32DegenerateTriangles':degenerates,
            'minimumZ':min_height,'maximumZ':max_height}


def main():
    started=time.time();report={'scope':'Isolated actual-floor geometry, not a full world build or Unity/VRChat run','floors':[],'fixtures':[]}
    manifest=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    report['moduleSha256']=hashlib.sha256((Path(__file__).parent/'deck_surface.py').read_bytes()).hexdigest()
    report['floorInputsSha256']=hashlib.sha256(json.dumps(manifest['floors'],sort_keys=True).encode()).hexdigest()
    for floor in manifest['floors']:
        p=wkt.loads(floor['wkt']);z=floor['z']-(100 if floor['z']>100 else 0)
        g=geometry();g.group='Decks/'+floor['level'];state=np.random.get_state()
        stats=add_deck_surface(g,p,z,M)
        assert g.group=='Decks/'+floor['level']
        image_fields=('texture','normal','arm','height')
        old_images={m.get(field) for m in manifest['materials'] for field in image_fields if m.get(field)}
        new_images={m.get(field) for m in g.materials.values() for field in image_fields if m.get(field)}
        assert new_images<=old_images,'added a texture image'
        assert all(np.array_equal(a,b) for a,b in zip(state,np.random.get_state())),'advanced global RNG'
        validation=inspect(g,p,z)
        assert not validation['float32DegenerateTriangles'],validation
        gg=geometry();gg.group=g.group;again=add_deck_surface(gg,p,z,M)
        assert stats==again and digest(g)==digest(gg),'not deterministic'
        old=geometry();old.group=g.group;old_count=old_deck(old,p,z)
        entry={'level':floor['level'],**stats,**validation,'oldSlabSeamsAndNailsTriangles':old_count,
               'vertices':sum(len(b['v']) for b in g.batches.values()),
               'oldVertices':sum(len(b['v']) for b in old.batches.values()),
               'savedTriangles':old_count-stats['triangles'],'sha256':digest(g)}
        report['floors'].append(entry);print(json.dumps(entry),flush=True)
    # Holes, disconnected parts, several concavities and narrower-than-bevel tips.
    fixtures={
      'concave_hole':Polygon([(0,0),(3,0),(3,2),(1.8,2),(1.8,4),(.2,4),(.2,2),(0,2)],
                       holes=[[(.55,.55),(.55,1.7),(1.25,1.7),(1.25,.55)]]),
      'multi_clipped':MultiPolygon([box(-.3,-.03,.1,.15),Polygon([(1,0),(2,.05),(1.0002,.25)])]),
      'ring_and_narrow_tongue':Point(0,0).buffer(2,quad_segs=16).difference(Point(0,0).buffer(1,quad_segs=16)).union(box(1.9,-.002,2.6,.002)),
      'hole_across_joint':box(0,0,2,5).difference(box(.279,2.1,.561,3.2)),
    }
    for name,p in fixtures.items():
        g=geometry();g.group='Decks/Fixture';stats=add_deck_surface(g,p,42,M)
        checked=inspect(g,p,42);assert not checked['float32DegenerateTriangles'],checked
        report['fixtures'].append({'name':name,**stats,**checked})
    report['newTriangles']=sum(f['triangles'] for f in report['floors'])
    report['oldTriangles']=sum(f['oldSlabSeamsAndNailsTriangles'] for f in report['floors'])
    report['savedTriangles']=report['oldTriangles']-report['newTriangles']
    report['newVertices']=sum(f['vertices'] for f in report['floors'])
    report['oldVertices']=sum(f['oldVertices'] for f in report['floors'])
    assert report['newTriangles']<=report['oldTriangles'],'exceeded old deck triangle budget'
    report['elapsedSeconds']=round(time.time()-started,3)
    report['status']='PASS'
    (ROOT/'Docs/deck_module_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('floors','fixtures')}),flush=True)

if __name__=='__main__':main()
