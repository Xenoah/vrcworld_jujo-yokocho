"""Conservative projection bound, not a Unity/GPU measurement."""
import json,sys,math
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box,Point
from shapely.ops import unary_union
from peer_culling_contract import read_visual
root=Path(sys.argv[1]);data=root/'Assets/TreeTopYokocho/Data';m=json.loads((data/'WorldManifest.json').read_text())
s=[b for b in read_visual(data/'VisualMeshes.bytes') if b['group'].startswith('Landscape/Sea_')];c=read_visual(data/'CollisionMeshes.bytes');v=np.concatenate([b['vertices'] for b in c]);lo=v.min(axis=0);hi=v.max(axis=0)
p=unary_union([Polygon(t[:,:2]) for b in s for t in b['vertices'][b['faces']]])
d=p.distance(box(lo[0]-1,lo[1]-1,hi[0]+1,hi[1]+1));nearest=None
for a in m['floorTests']:
 v=np.asarray(a['position']);z=s[0]['vertices'][0,2];dist=math.hypot(p.distance(Point(v[:2])),v[2]+1.65-z)
 if nearest is None or dist<nearest['distanceMetres']:nearest=dict(distanceMetres=dist,floorSample=a,eyeHeightMetres=1.65)
delta=.043;width=1280;height=720;hfov=math.radians(60)
focal=width/(2*math.tan(hfov/2))
# Finite perspective bound for the entire rectangular frustum, including its
# diagonal. Expand corner angle for a point moving into the frustum, and
# shrink radial distance by delta. Projection Jacobian is bounded by sec².
corner=math.atan(math.hypot(1,height/width)*math.tan(hfov/2))+math.asin(delta/(d-delta))
conservative=focal*delta/math.cos(corner)/((d-delta)*math.cos(corner)-delta)
report=dict(originalVertexAmplitudeUpperBoundMetres=.043,newVertexAmplitudeMetres=0,originalWavelengthMetres=[2*math.pi/.13,2*math.pi/.19],shaderAnimationAfter='world-space fragment ripple normals',collisionBounds=[lo.tolist(),hi.tolist()],collisionBoundsXYExpansionMetres=1,horizontalDistanceLowerBoundMetres=d,nearestSampledLegalEye=nearest,maximumAngularChangeDegrees=math.degrees(math.atan(.043/d)),referenceHorizontalFovDegrees=60,referenceWidthPixels=width,referenceHeightPixels=height,angularLinearPixelEstimate=width*math.atan(delta/d)/hfov,conservativeFullFrustumPixelBound=conservative,limitations='Finite perspective bound assumes 1280x720 ordinary 60-degree horizontal-FOV camera; includes off-axis diagonal and displacement margins. Not a rendered Unity motion test. Bound covers collider XY AABB expanded one metre, not arbitrary flying cameras. Vertex displacement removal is coordinated with fragment ripple shader, not claimed geometrically identical animation.')
print(json.dumps(report,indent=2))
