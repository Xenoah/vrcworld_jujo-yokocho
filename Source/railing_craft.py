"""Continuous, joinery-led deck railings with metre-spaced posts.

The old renderer restarted posts for every polygon edge. On a round deck that
made two posts at almost every 0.45m chord. This code joins adjacent chords
before spacing posts, so the view opens up without changing a safety collider.
"""
import math
import numpy as np
from shapely.geometry import MultiLineString
from shapely.ops import linemerge


def add_railing_runs(g, segments, z, m):
    original=g.group;g.group=original+'/HandCraft'
    if not segments:return {'runs':0,'posts':0,'length':0}
    joined=linemerge(MultiLineString(segments))
    runs=list(joined.geoms) if hasattr(joined,'geoms') else [joined]
    total=posts=0
    up=np.array([0,0,1.]);wood=m['wood'];dark=m['dark'];iron=m['iron'];trim=m['trim']
    def point(line,s,height=0):
        p=line.interpolate(float(np.clip(s,0,line.length)))
        return np.array([p.x,p.y,z+height])
    for line in runs:
        # A nine-millimetre visual chord tolerance removes needlessly tiny
        # rail pieces; the independently generated collision boundary is exact.
        line=line.simplify(.009,preserve_topology=True)
        if line.length < .055:continue
        total+=line.length
        coords=list(line.coords)
        for aa,bb in zip(coords,coords[1:]):
            a=np.array([*aa,z]);b=np.array([*bb,z])
            for h,width,depth in [(.50,.063,.070),(1.12,.098,.074)]:
                g.beam(a+up*h,b+up*h,width,dark,depth)
            # Slightly larger top member is the hand-polished wearing surface.
            g.beam(a+up*1.19,b+up*1.19,.110,wood,.056)
        n=max(1,math.ceil(line.length/1.45))
        closed=line.is_ring
        for j in range(n if closed else n+1):
            s=j*line.length/n;p=point(line,s)
            tangent=point(line,s+.04)-point(line,s-.04)
            if np.linalg.norm(tangent)<1e-8:tangent=np.r_[np.asarray(coords[1])-coords[0],0.]
            tangent/=np.linalg.norm(tangent);normal=np.cross(up,tangent)
            axes=[tangent,normal,up]
            g.box(p+up*.60,[.126,.126,1.20],wood,axes)
            g.box(p+up*1.22,[.17,.17,.062],dark,axes)
            g.box(p+up*.055,[.156,.156,.075],iron,axes)
            # A low through-band and two real hex bolt heads each side.
            for side in (-1,1):
                g.box(p+normal*side*.067+up*.36,[.127,.015,.096],iron,axes)
                for hz in (.36,):
                    a=p+normal*side*.076+up*hz
                    g.tube([a,a+normal*side*.007],[.010,.010],trim,6)
            posts+=1
        # Narrow infill belongs to the lower field, leaving the eye-level view
        # open like the concept. It does not replace the invisible full wall.
        for s in np.arange(.18,line.length-.1,.34):
            if min(abs(s-j*line.length/n) for j in range(n+1))<.12:continue
            p=point(line,s);g.beam(p+up*.09,p+up*.48,.031,wood,.038)
    g.group=original
    return {'runs':len(runs),'posts':posts,'length':round(total,3),'maximumPostSpacing':1.45}
