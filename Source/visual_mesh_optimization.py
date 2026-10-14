"""Lossless visual-only compaction. No welding, decimation or face reordering.

Run after UV repair and Color32 baking, before BOTH native and GLB exports.
Never call on collision geometry. Existing vertex equivalence classes survive:
normal/tangent accumulation is unchanged for every referenced vertex.
"""
import numpy as np


def retained_vertex_indices(vertices,faces):
    used=np.unique(faces)
    v=np.asarray(vertices)
    if len(used):
        # RecalculateBounds includes unreferenced vertices in Unity. Preserve
        # exact original bounds with minimal extrema anchors when necessary.
        extra=[]
        for axis in range(3):
            for op in (np.argmin,np.argmax):
                i=int(op(v[:,axis]));j=used[int(op(v[used,axis]))]
                if v[i,axis]!=v[j,axis]:extra.append(i)
        if extra:used=np.unique(np.r_[used,np.asarray(extra,np.uint32)])
    return used


def compact_unused_visual_vertices(geometry):
    records=[]
    for (group,material), batch in geometry.batches.items():
        before=len(batch['v']); faces=np.asarray(batch['f'],dtype=np.uint32)
        used=retained_vertex_indices(batch['v'],faces)
        if len(used)==before:continue
        # Empty batches are not silently deleted: identities/order are retained.
        inverse=np.full(before,np.iinfo(np.uint32).max,dtype=np.uint32)
        inverse[used]=np.arange(len(used),dtype=np.uint32)
        batch['f']=inverse[faces]
        for attr in ('v','uv','colors'):
            if attr in batch:batch[attr]=np.asarray(batch[attr])[used].copy()
        # Source tint intervals were consumed by bake_mood; stale intervals
        # must never later be interpreted against the compacted index space.
        batch.pop('authored_tints',None)
        records.append(dict(group=group,material=material,beforeVertices=before,
                            afterVertices=len(used),triangles=len(faces),
                            savedNativeBytes=(before-len(used))*24))
    return dict(version=1,algorithm='remove-unreferenced-vertices-only',
                modifiedBatches=len(records),removedVertices=sum(x['beforeVertices']-x['afterVertices'] for x in records),
                savedNativeBytes=sum(x['savedNativeBytes'] for x in records),batches=records)


SEA_KEYS=tuple(('Landscape/Sea_'+str(i),'Lake') for i in range(4))


def simplify_planar_sea(geometry):
    """Retriangulate four static sea sheets, retaining every boundary sample.

    Requires coordinated static-vertex Water shader. This is not suitable for
    any displaced surface, foliage, clouds, near timber or collision geometry.
    """
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import Polygon
    records=[]
    for key in SEA_KEYS:
        b=geometry.batches[key];v=np.asarray(b['v']);f=np.asarray(b['f'])
        if v.shape!=(775,3) or f.shape!=(1440,3):raise ValueError('Unexpected sea source topology: '+str(key))
        if not np.all(v[:,2]==v[0,2]):raise ValueError('Sea is not exactly planar')
        if not np.all(b['colors']==b['colors'][0]):raise ValueError('Sea colors are not constant')
        # Source ocean UV is globally affine; any authored non-affine paint
        # needs the original grid. Permit only float32 packing error.
        if np.max(np.abs(np.asarray(b['uv'],float)-v[:,:2].astype(float)*.018))>=1e-5:
            raise ValueError('Sea UV field is not the approved affine projection')
        edges=np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]))
        canonical=np.sort(edges,axis=1)
        _,inverse,counts=np.unique(canonical,axis=0,return_inverse=True,return_counts=True)
        boundary=edges[counts[inverse]==1]
        next_vertex={int(a):int(z) for a,z in boundary}
        if len(next_vertex)!=108:raise ValueError('Unexpected sea boundary')
        start=min(next_vertex);loop=[start];cursor=next_vertex[start]
        while cursor!=start:
            if cursor in loop:raise ValueError('Non-simple sea boundary')
            loop.append(cursor);cursor=next_vertex[cursor]
        if len(loop)!=108:raise ValueError('Multiple sea boundaries')
        selected=np.asarray(loop,np.uint32);pv=v[selected];poly=Polygon(pv[:,:2])
        if not poly.is_valid:raise ValueError('Invalid sea outline')
        lookup={tuple(p[:2]):i for i,p in enumerate(pv)};tri=[]
        for triangle in constrained_delaunay_triangles(poly).geoms:
            ids=[lookup[tuple(p)] for p in list(triangle.exterior.coords)[:3]]
            p=pv[ids].astype(float)
            if np.cross(p[1]-p[0],p[2]-p[0])[2]<0:ids=ids[::-1]
            tri.append(ids)
        if len(tri)!=106:raise ValueError('Unexpected sea triangulation')
        b['f']=np.asarray(tri,np.uint32)
        for attr in ('v','uv','colors'):b[attr]=np.asarray(b[attr])[selected].copy()
        b.pop('authored_tints',None)
        records.append(dict(group=key[0],material=key[1],beforeVertices=775,afterVertices=108,beforeTriangles=1440,afterTriangles=106,savedNativeBytes=667*24+1334*12))
    return dict(version=1,algorithm='exact-boundary-planar-sea-cdt',removedVertices=2668,removedTriangles=5336,savedNativeBytes=128064,batches=records)
