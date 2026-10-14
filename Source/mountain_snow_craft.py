"""Separate snow-retention revision; selected soft pins live in quality v2.

Uses existing height, slope and broad convexity, never baked light direction.
It changes only eight snow Color32 payloads; no geometry/material/UV changes.
All dark sublevel components must remain connected to the original rock edge.
"""
import heapq
import hashlib
import numpy as np
from fantasy_landscape import _mountain_height,_mountain_snow_coverage


def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0.,1.);return t*t*(3-2*t)


def surface_retention(points,strength='balanced'):
    x,y,z=np.asarray(points).T
    # Broad 160 m neighborhoods follow the authored range, not added texture
    # noise. Convex exposed shoulders shed snow; concave hollows retain it.
    step=80.
    samples=np.array([[_mountain_height(xx,yy),_mountain_height(xx+step,yy),_mountain_height(xx-step,yy),_mountain_height(xx,yy+step),_mountain_height(xx,yy-step)] for xx,yy in zip(x,y)])
    h,xp,xm,yp,ym=samples.T;slope=np.hypot((xp-xm)/(2*step),(yp-ym)/(2*step));convex=h-(xp+xm+yp+ym)/4
    if strength=='balanced':a,b,amount=.76,1.30,.87
    elif strength=='strong':a,b,amount=.66,1.20,.94
    else:raise ValueError('Unknown bounded snow-craft study')
    steep=smooth(a,b,slope);crest=smooth(10.,55.,convex);shelter=smooth(0.,32.,-convex)
    stress=amount*steep+.50*crest*(.30+.70*steep)-.28*shelter
    retention=1-smooth(.20,.80,stress)
    return _mountain_snow_coverage(points)*retention


def softened_retention(raw,points,faces):
    """Broad object-space accumulation without darkening existing white crests.

    Projected dual-area weights remove adaptive vertex-density bias. A 65 m
    Gaussian only adds snow near exposed margins, rounding triangular cuts;
    it does not paint a camera- or light-dependent shadow into the material.
    """
    from scipy.spatial import cKDTree
    points=np.asarray(points);faces=np.asarray(faces,int);q=points[faces,:2]
    area=np.abs((q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0]))/6
    weights=np.zeros(len(points));np.add.at(weights,faces.ravel(),np.repeat(area,3))
    neighbors=cKDTree(points[:,:2]).query_ball_point(points[:,:2],180.,return_sorted=True)
    filtered=np.asarray(raw).copy()
    for i,ids in enumerate(neighbors):
        ids=np.asarray(ids,int);distance=np.sum((points[ids,:2]-points[i,:2])**2,axis=1)
        w=np.exp(-distance/(2*65.**2))*weights[ids]
        if w.sum()>1e-12:filtered[i]=float(np.sum(w*raw[ids])/w.sum())
    return np.maximum(raw,.85*filtered+.15*raw)


def connected_cover(raw,faces,boundary,points=None):
    raw=np.asarray(raw).copy();raw[boundary]=0.;neighbors=[set() for _ in raw]
    for a,b,c in faces:neighbors[a].update((b,c));neighbors[b].update((a,c));neighbors[c].update((a,b))
    cover=np.ones(len(raw));queue=[]
    for i in boundary:cover[i]=0.;heapq.heappush(queue,(0.,i))
    while queue:
        value,i=heapq.heappop(queue)
        if value!=cover[i]:continue
        for j in sorted(neighbors[i]):
            # A shallow geodesic accumulation ramp avoids constant gray
            # bottleneck plateaus while preserving every dark sublevel path.
            ramp=0. if points is None else .00020*float(np.linalg.norm(points[i,:2]-points[j,:2]))
            candidate=min(1.,max(value,raw[j])+ramp)
            if candidate<cover[j]:cover[j]=candidate;heapq.heappush(queue,(candidate,j))
    return cover


def apply_mountain_snow_craft(g,strength='soft'):
    """Selected soft alternative to apply_snow_deposition(), not applied after it."""
    from mountain_detail_contract import KEYS,load_oracle
    if {k for k in g.batches if k[0].startswith('Landscape/SnowRange_')}!=set(KEYS):
        raise ValueError('Snow craft requires exact twelve adaptive mountain batches')
    for key,pin in zip(KEYS,load_oracle()['variants']['after_plain']):
        batch=g.batches[key]
        if batch.get('authored_tints') or 'colors' in batch:raise ValueError('Snow craft must precede color authoring')
        v=np.asarray(batch['v'],dtype='<f4');uv=np.asarray(batch['uv'],dtype='<f4');f=np.asarray(batch['f'],dtype='<u4')
        payload=v.tobytes()+uv.tobytes()+np.full((len(v),4),255,dtype='u1').tobytes()+f.tobytes()
        if hashlib.sha256(payload).hexdigest()!=pin['attributesAndIndicesSha256']:
            raise ValueError('Snow craft input differs from exact approved adaptive source')
    keys=[('Landscape/SnowRange_%d'%i,m) for i in range(4) for m in ('AlpineSnow','AlpineSnowShade')]
    if any(g.batches[k].get('authored_tints') or 'colors' in g.batches[k] for k in keys):raise ValueError('Apply snow craft before all snow tints and color baking')
    key_for=lambda p:tuple(np.round(p,6));rock={key_for(p) for i in range(4) for p in g.batches[('Landscape/SnowRange_%d'%i,'AlpineRock')]['v']}
    lookup={};points=[];faces=[];batchids={}
    for key in keys:
        batch=g.batches[key];ids=[]
        for p in batch['v']:
            q=key_for(p)
            if q not in lookup:lookup[q]=len(points);points.append(p)
            ids.append(lookup[q])
        batchids[key]=np.asarray(ids,dtype=int);faces.extend(batchids[key][np.asarray(batch['f'],int)].tolist())
    boundary=[i for p,i in lookup.items() if p in rock];points=np.asarray(points);raw=surface_retention(points,'balanced' if strength=='soft' else strength)
    if strength=='soft':raw=softened_retention(raw,points,faces)
    cover=connected_cover(raw,faces,boundary,points=points if strength=='soft' else None)
    rockcolor=np.array((.025,.028,.0055))
    for key,ids in batchids.items():
        base=np.array((.88,.93,.97) if key[1]=='AlpineSnow' else (.60,.72,.82));weight=cover[ids,None];color=rockcolor*(1-weight)+base*.95*weight
        g.batches[key].setdefault('authored_tints',[]).append((0,len(ids),np.clip(color/base,0,1)))
    return {'version':1,'study':strength,'changedSnowBatches':8,'trianglesAdded':0,'points':len(points),'rockBoundaryVertices':len(boundary),'rawCoveragePercentiles':np.percentile(raw,[0,10,25,50,75,90,100]).tolist(),'connectedCoveragePercentiles':np.percentile(cover,[0,10,25,50,75,90,100]).tolist(),'highAltitudeCoveragePercentiles':np.percentile(cover[points[:,2]>550],[0,10,25,50,75,90,100]).tolist(),'connectivityFilledVertices':int(np.sum(cover>raw+1e-10))}
