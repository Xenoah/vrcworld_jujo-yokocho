"""Exact distance to authored route polylines, plus conservative width bounds."""
import json,sys,math
from pathlib import Path
import numpy as np
r=json.loads(Path(sys.argv[1]).read_text());m=json.loads(Path(sys.argv[2]).read_text());routes=[]
for route in m['crownStairs']['routes']:routes.append(dict(name=route['name'],points=route['points'],width=route['width']))
for route in m['navigationPaths']+[m['mainRingNavigation']]:routes.append(dict(name=route['id'],points=[[*p,route['z']] for p in route['points']],width=route['width']))
for route in m['stairs']:routes.append(dict(name=route['id']+'_approximateSlope',points=[route['start'],route['end']],width=route['width']))
a=[];b=[];widths=[];names=[]
for route in routes:
 points=np.asarray(route['points'],float)+[0,0,1.65]
 for start,end in zip(points[:-1],points[1:]):
  if np.linalg.norm(end-start)<1e-9:continue
  a.append(start);b.append(end);widths.append(route['width']/2);names.append(route['name'])
a=np.asarray(a);b=np.asarray(b);direction=b-a;squared=np.sum(direction**2,axis=1);widths=np.asarray(widths)
components=r['components'];output=[]
for offset in range(0,len(components),256):
 chunk=components[offset:offset+256];p=np.asarray([x['center'] for x in chunk]);delta=p[:,None,:]-a[None,:,:];t=np.clip(np.sum(delta*direction[None,:,:],axis=2)/squared,0,1);difference=delta-t[:,:,None]*direction;distance=np.linalg.norm(difference,axis=2);minimum=np.argmin(distance,axis=1);wide_min=np.argmin(distance-widths[None,:],axis=1)
 for i,c in enumerate(chunk):
  index=int(minimum[i]);wi=int(wide_min[i]);record=dict(c);record.update(nearestContinuousRoute=names[index],nearestContinuousRouteEye=(a[index]+t[i,index]*direction[index]).tolist(),centerDistanceToContinuousRoute=float(distance[i,index]),continuousRouteSphereDistanceLowerBound=max(0,float(distance[i,index])-c['boundingRadius']),walkableWidthSphereDistanceLowerBound=max(0,float(distance[i,wi])-widths[wi]-c['boundingRadius']-.30));output.append(record)
r['components']=output;r['continuousRouteAudit']=dict(routes=len(routes),segments=len(a),eyeHeight=1.65,additionalTreadMarginMetres=.30,scope='Exact distance from component AABB center to named source route-eye polylines. Subtracting component bounding radius, route half-width and0.30m gives conservative corridor-envelope lower bound. Original three legacy stairs represented by straight slope, covered by margin. Not a visibility test or all possible deck-floor viewpoints.')
Path(sys.argv[3]).write_text(json.dumps(r,indent=2));print(json.dumps(r['continuousRouteAudit']))
