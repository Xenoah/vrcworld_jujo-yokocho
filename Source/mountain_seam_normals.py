"""Separately gated exact-12 seam-only normal sharing, no geometry edits.

Operate on native float32 XYZ and uint32 indices. Only coincident vertices in
multiple approved batches are eligible; every endpoint of a >55 degree actual
mesh crease is excluded. Interior vertices/unrelated mesh normals stay exact.
The Unity Editor helper mirrors this source-coordinate, corner-angle kernel.
"""
import hashlib,math
from collections import defaultdict
import numpy as np
from mountain_detail_contract import KEYS,load_oracle

CREASE_COSINE=0.5735764363510462  # cos(55 degrees), shared literal with C#.


def _kernel(batches):
    """Deterministic kernel, separately tested under face/vertex permutations.

    Production admission is seam_normal_overrides(), not this private helper.
    Canonical coordinate triangle ordering fixes summation order independently
    of input batch, face, vertex and dictionary iteration order.
    """
    lookup={};points=[];owners=defaultdict(set);batchids={};triangles=[]
    for b in batches:
        key=(b['group'],b['material']);v=np.asarray(b['vertices'],dtype='<f4');f=np.asarray(b['faces'],dtype='<u4')
        if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():raise ValueError('Invalid normal-source positions')
        if f.ndim!=2 or f.shape[1]!=3 or not len(f) or int(f.max())>=len(v):raise ValueError('Invalid normal-source indices')
        ids=[]
        for p in v:
            coord=tuple(map(float,p))
            if coord not in lookup:lookup[coord]=len(points);points.append(coord)
            i=lookup[coord];ids.append(i);owners[i].add(key)
        ids=np.asarray(ids);batchids[key]=ids
        for face in f:
            coords=[tuple(map(float,p)) for p in v[face]];start=min(range(3),key=lambda i:coords[i]);coords=coords[start:]+coords[:start]
            globalids=list(map(int,ids[face]));globalids=globalids[start:]+globalids[:start]
            triangles.append((tuple(coords),tuple(globalids)))
    triangles.sort(key=lambda row:row[0]);facets=[];edges=defaultdict(list);summed=np.zeros((len(points),3),float)
    for fid,(coords,ids) in enumerate(triangles):
        p=np.asarray(coords,float);cross=np.cross(p[1]-p[0],p[2]-p[0]);length=float(np.linalg.norm(cross))
        if not math.isfinite(length) or length<=1e-12:raise ValueError('Degenerate triangle in normal source')
        normal=cross/length;facets.append(normal)
        for corner in range(3):
            a=p[(corner+1)%3]-p[corner];b=p[(corner+2)%3]-p[corner]
            angle=math.atan2(float(np.linalg.norm(np.cross(a,b))),float(a@b))
            if not math.isfinite(angle) or angle<=0:raise ValueError('Invalid triangle corner angle')
            summed[ids[corner]]+=normal*angle
            x,y=ids[corner],ids[(corner+1)%3];edges[(min(x,y),max(x,y))].append(fid)
    crease=set();sharp_edges=0
    for (a,b),ff in edges.items():
        if len(ff)>2:raise ValueError('Non-manifold mountain normal input')
        if len(ff)==2 and float(np.dot(facets[ff[0]],facets[ff[1]]))<CREASE_COSINE:crease.update((a,b));sharp_edges+=1
    seam={i for i,own in owners.items() if len(own)>1};eligible=seam-crease;result={}
    lengths=np.linalg.norm(summed,axis=1)
    if any(not math.isfinite(lengths[i]) or lengths[i]<=1e-12 for i in eligible):raise ValueError('Zero or invalid seam normal')
    normals=summed/np.maximum(lengths[:,None],1e-20)
    for key,ids in batchids.items():
        selected=np.array([i for i,gid in enumerate(ids) if int(gid) in eligible],dtype=np.int32);result[key]=(selected,normals[ids[selected]].astype(np.float32))
    stats=dict(inputBatches=len(batches),uniqueCoincidentSeamPositions=len(seam),eligibleSharedPositions=len(eligible),excludedSharpSeamPositions=len(seam&crease),allSharpEdgeCount=sharp_edges,creaseAngleDegrees=55.,changedNormalSlots=sum(len(v[0]) for v in result.values()),geometryBytesChanged=0,colorBytesChanged=0,uvBytesChanged=0,scope='Source normal override only; Unity execution not yet verified')
    return result,stats


def seam_normal_overrides(batches):
    """Admit only exact approved adaptive11 geometry, then compute overrides."""
    bykey={(b['group'],b['material']):b for b in batches}
    if set(bykey)!=set(KEYS) or len(batches)!=12:raise ValueError('Seam normals require exact twelve mountain inputs')
    for key,pin in zip(KEYS,load_oracle()['variants']['after_plain']):
        b=bykey[key];v=np.asarray(b['vertices'],dtype='<f4');f=np.asarray(b['faces'],dtype='<u4')
        if hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest()!=pin['geometrySha256']:raise ValueError('Unapproved mountain geometry for normal pass')
    return _kernel([bykey[k] for k in KEYS])
