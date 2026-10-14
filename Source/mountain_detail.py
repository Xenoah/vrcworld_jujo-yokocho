"""Bounded adaptive refinement of the existing seven-summit mountain field.

This opt-in authoring pass replaces exactly twelve visual batches before snow
color deposition. No RNG, materials, collisions, lights or other mesh fields.
The source height function is intentionally untouched. Curvature residuals,
not uniform subdivision, determine sampling density. Shared integer edge keys
make transitions conforming across cells, sectors and snow-material clipping.
"""
from collections import defaultdict
from scipy.spatial import Delaunay
import math
import hashlib
import numpy as np
from fantasy_landscape import _mountain_height, _clip_snow

MATERIALS = ('AlpineRock', 'AlpineSnow', 'AlpineSnowShade')
KEYS = tuple(('Landscape/SnowRange_%d' % i, m) for i in range(4) for m in MATERIALS)
ERROR_METRES = 11.0
# Exact uncolored old source payloads, before the adaptive pass.
SOURCE_PINS = {('Landscape/SnowRange_0', 'AlpineRock'): '039408fd2e12a0fbe8e37e46fbd1e433331e401398386f95898a2cfd0eb861f2', ('Landscape/SnowRange_0', 'AlpineSnow'): 'dc472cac57e36708b92acd51c8b119a2aec95143014b41cf5875821b138049da', ('Landscape/SnowRange_0', 'AlpineSnowShade'): 'af107d0e31cb79937005568a9c0ae393a8cb1cf99869f43d7fed4ed8793a87bf', ('Landscape/SnowRange_1', 'AlpineRock'): '09d3adae09f99be4a43861c6600fff7614e1bb8acb7307e5e9dc1939707773a9', ('Landscape/SnowRange_1', 'AlpineSnow'): '5112311fdd84f8c490325a666bc4a6da22a305dc8b842a0dc654b36711ed97eb', ('Landscape/SnowRange_1', 'AlpineSnowShade'): '7d39ca1e012f878166c982a4a9060a315e96356e5669437dba55faac7a9c2f3f', ('Landscape/SnowRange_2', 'AlpineRock'): 'dc31be56eaff3ffa95147d7826aeda931645356588af89d9773f71faea480c11', ('Landscape/SnowRange_2', 'AlpineSnow'): '7115c7079fbb25cf425bf3d1466515801ae9ea0b224349de2e3cb6f11541d1c2', ('Landscape/SnowRange_2', 'AlpineSnowShade'): '293f431c2fc79a5e2712c819024a557cfa570c8335ba41c38f890f02453a0ebf', ('Landscape/SnowRange_3', 'AlpineRock'): '9728992380d872e0bc1d6b9afabe48e79a07a58cb7539e911079cf3bdb33167b', ('Landscape/SnowRange_3', 'AlpineSnow'): 'fb764c6061e2f369cd86e60a9e74df828aa55e77cbe6034372bbe59d687cc84e', ('Landscape/SnowRange_3', 'AlpineSnowShade'): 'b3d98e10b2f489d1dbe815689639cdcf445d16ae67159a351dc460b68e3020ae'}
# Four subintervals per original interval, with 2 x 2 original-cell roots.
NX, NY = 416, 196


def adaptive_surface(error_metres=ERROR_METRES):
    """Return four crack-free sector meshes and source-space error metadata."""
    points = {}
    def point(ix, iy):
        key = (ix, iy)
        if key not in points:
            x, y = -3000. + ix*(6000./NX), 1240. + iy*(2620./NY)
            points[key] = np.array((x, y, _mountain_height(x, y)))
        return points[key]
    leaves = []
    errors = []
    def visit(x0, y0, x1, y1, level):
        xm, ym = (x0+x1)/2, (y0+y1)/2
        a,b,c,d = [point(*k) for k in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]
        samples = [(xm,y0), (x1,ym), (xm,y1), (x0,ym), (xm,ym)]
        predicted = [(a[2]+b[2])/2, (b[2]+c[2])/2, (c[2]+d[2])/2,
                     (d[2]+a[2])/2, (a[2]+c[2])/2]
        residual = max(abs(point(*k)[2]-z) for k,z in zip(samples,predicted))
        # The upper shoulder and skyline are perceptually prominent from the
        # unchanged decks. Keep finer source approximation there, not planar
        # fringe fields that merely occupy a large surface area.
        importance = 1.35 if max(a[2],b[2],c[2],d[2]) > 380 else 1.
        if level < 3 and min(x1-x0,y1-y0) >= 2 and residual*importance > error_metres:
            visit(x0,y0,xm,ym,level+1); visit(xm,y0,x1,ym,level+1)
            visit(xm,ym,x1,y1,level+1); visit(x0,ym,xm,y1,level+1)
        else:
            leaves.append((x0,y0,x1,y1)); errors.append(residual)
    # Coarse roots cover the exact old XY rectangle, including its short last
    # Y row. Sector boundaries land on root boundaries at 0/104/208/312/416.
    for x0 in range(0,NX,8):
        for y0 in range(0,NY,8):
            visit(x0,y0,min(x0+8,NX),min(y0+8,NY),0)
    horizontal,vertical = defaultdict(set),defaultdict(set)
    for x0,y0,x1,y1 in leaves:
        horizontal[y0].update((x0,x1));horizontal[y1].update((x0,x1))
        vertical[x0].update((y0,y1));vertical[x1].update((y0,y1))
    # Preserve every old sector/domain boundary sample, even where adjacent
    # planar regions use only a root cell. Both sides consume the same keys.
    for x in range(0,NX+1,104):vertical[x].update(range(0,NY+1,4))
    for y in (0,NY):horizontal[y].update(range(0,NX+1,4))
    sectors=[([],[],{}) for _ in range(4)]
    size_histogram=defaultdict(int)
    for x0,y0,x1,y1 in leaves:
        ring = ([(x,y0) for x in sorted(horizontal[y0]) if x0<=x<x1]
              + [(x1,y) for y in sorted(vertical[x1]) if y0<=y<y1]
              + [(x,y1) for x in sorted(horizontal[y1],reverse=True) if x0<x<=x1]
              + [(x0,y) for y in sorted(vertical[x0],reverse=True) if y0<y<=y1])
        sector=min(3,int(x0//104));vv,ff,lookup=sectors[sector]
        def vertex(k):
            if k not in lookup:lookup[k]=len(vv);vv.append(point(*k))
            return lookup[k]
        ids=[vertex(k) for k in ring]
        if len(ids)==4:
            centre=point((x0+x1)/2,(y0+y1)/2)[2]
            if abs(centre-(vv[ids[0]][2]+vv[ids[2]][2])/2) <= abs(centre-(vv[ids[1]][2]+vv[ids[3]][2])/2):
                ff.extend([(ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])])
            else:ff.extend([(ids[0],ids[1],ids[3]),(ids[1],ids[2],ids[3])])
        else:
            # A constrained convex leaf needs n-2, not n centre-fan faces.
            # Delaunay retains all collinear boundary samples without adding
            # interior vertices; leaf edges remain shared exactly.
            local=Delaunay(np.asarray(ring,dtype=float))
            for tri in local.simplices:
                mapped=[ids[int(i)] for i in tri]
                p=np.asarray([vv[i] for i in mapped])
                if np.cross(p[1]-p[0],p[2]-p[0])[2]<0:mapped.reverse()
                ff.append(tuple(mapped))
        size_histogram['%g'%(x1-x0)]+=1
    return [(np.asarray(v),np.asarray(f,dtype=np.uint32)) for v,f,_ in sectors], {
        'leafCells':len(leaves),'cellFineUnitWidths':dict(sorted(size_histogram.items())),
        'maxLeafProbeResidualMetres':max(errors),'errorThresholdMetres':error_metres,
        'unclippedTriangles':sum(len(f) for _,f,_ in sectors),
    }


def refined_batches(error_metres=ERROR_METRES):
    """Build the established twelve material/sector records, no new identity."""
    sectors,stats=adaptive_surface(error_metres);result={}
    for sector,(v,f) in enumerate(sectors):
        mesh={m:([],[],[]) for m in MATERIALS}
        def add_poly(poly,material):
            if len(poly)<3:return
            vv,ff,uv=mesh[material];k=len(vv);vv.extend(poly)
            uv.extend([[p[0]*.012,p[1]*.012] for p in poly])
            ff.extend((k,k+i,k+i+1) for i in range(1,len(poly)-1))
        for ids in f:
            tri=list(v[ids]);vals=[p[2]-(310+12*math.sin(p[0]*.003)+5*math.cos(p[1]*.003)) for p in tri]
            add_poly(_clip_snow(tri,vals,False),MATERIALS[0])
            normal=np.cross(tri[1]-tri[0],tri[2]-tri[0])
            snowy=MATERIALS[2] if normal[1]>abs(normal[2])*.68 and sum(p[1] for p in tri)/3>2250 else MATERIALS[1]
            add_poly(_clip_snow(tri,vals,True),snowy)
        for material,(vv,ff,uv) in mesh.items():
            if not ff:raise ValueError('Refinement lost a required mountain batch')
            vv=np.asarray(vv);ff=np.asarray(ff)
            _,index,inverse=np.unique(np.round(vv,6),axis=0,return_index=True,return_inverse=True)
            vv=vv[index];ff=inverse[ff]
            area=np.linalg.norm(np.cross(vv[ff[:,1]]-vv[ff[:,0]],vv[ff[:,2]]-vv[ff[:,0]]),axis=1)
            result[('Landscape/SnowRange_%d'%sector,material)]={'v':vv.tolist(),'f':ff[area>1e-8].tolist(),'uv':np.asarray(uv)[index].tolist()}
    stats.update(triangles=sum(len(b['f']) for b in result.values()),vertices=sum(len(b['v']) for b in result.values()),modifiedBatches=12)
    return result,stats


def apply_mountain_detail(g):
    """Apply once before existing snow deposition, compact, UV repair and bake."""
    present={k for k in g.batches if k[0].startswith('Landscape/SnowRange_')}
    if present!=set(KEYS):raise ValueError('Mountain refinement expects exactly twelve original batches')
    if any(g.batches[k].get('authored_tints') or 'colors' in g.batches[k] for k in KEYS):
        raise ValueError('Mountain refinement must precede color deposition and baking')
    for key in KEYS:
        batch=g.batches[key]
        raw=b''.join(np.asarray(batch[a],dtype=d).tobytes() for a,d in [('v','<f4'),('uv','<f4'),('f','<u4')])
        if hashlib.sha256(raw).hexdigest()!=SOURCE_PINS[key]:
            raise ValueError('Mountain source differs from frozen original: '+str(key))
    old=sum(len(g.batches[k]['f']) for k in KEYS)
    replacements,stats=refined_batches()
    if old!=11500 or not 0<=stats['triangles']-old<=5000:
        raise ValueError('Unexpected mountain baseline or exceeded +5,000 triangle budget')
    for key in KEYS:g.batches[key]=replacements[key]
    return stats|{'beforeTriangles':old,'addedTriangles':stats['triangles']-old,'newTextures':0,'newMaterials':0,'newColliders':0}
