import sys,json,math
from pathlib import Path
import numpy as np
r=json.loads(Path(sys.argv[1]).read_text());components=r['components'];focal=1280/(2*math.tan(math.pi/6));corner=math.atan(math.hypot(1,720/1280)*math.tan(math.pi/6));scale=focal/(math.cos(corner)**2)
rows=[]
for family,radius in [('Scenery twigs / groves',.034),('Scenery twigs / peers',.072)]:
 parts=[p for p in components if p['family']==family and p['triangles']==30 and p['walkableWidthSphereDistanceLowerBound']>=100]
 lower=min(p['walkableWidthSphereDistanceLowerBound'] for p in parts);delta=radius*(1-math.cos(math.pi/4));theta=corner+math.asin(delta/(lower-delta));pixel_bound=focal*delta/math.cos(theta)/((lower-delta)*math.cos(theta)-delta)
 rows.append(dict(family=family,eligibleFiveSidedThreeRingStems=len(parts),existingTriangles=len(parts)*30,estimatedFourSidedTriangles=len(parts)*24,prospectiveTriangleSavings=len(parts)*6,prospectiveVertexSavings=len(parts)*3,prospectiveNativeByteSavings=len(parts)*(6*12+3*24),minimumCorridorEnvelopeDistanceMetres=lower,maximumStemRadius=radius,circumscribedVsInscribedRingProfileErrorMetres=delta,referenceFullFrustumRingProfilePixelBound=pixel_bound,scope='Audit estimate only. Ring radial-profile bound is not a complete loft/shading/UV error certificate. Four-sided forks and all leaf cards remain unchanged; no geometry generated or modified.'))
leaf=[]
for family in ['Host crown / folded leaves','Host framing / folded leaves']:
 parts=[p for p in components if p['family']==family]
 leaf.append(dict(family=family,count=len(parts),triangles=sum(p['triangles'] for p in parts),beyond30mCorridorEnvelope=sum(p['walkableWidthSphereDistanceLowerBound']>=30 for p in parts),beyond50mCorridorEnvelope=sum(p['walkableWidthSphereDistanceLowerBound']>=50 for p in parts),projectedDiameterPercentiles=np.percentile([p['referenceProjectedDiameterPixels'] for p in parts],[10,50,90]).tolist()))
forest=[p for p in components if p['family']=='Forest groves / opaque canopy' and p['triangles']==120]
forests=[]
for threshold in [300,400,500]:
 parts=[p for p in forest if p['walkableWidthSphereDistanceLowerBound']>=threshold]
 forests.append(dict(corridorDistanceThreshold=threshold,eligible120TriangleCrowns=len(parts),sourceTriangles=len(parts)*120,estimated12to8AngularSampleSaving=len(parts)*40,scope='Unvalidated upper opportunity estimate, not approved. No guaranteed silhouette/normal/coverage bound; lobed profiles need independent geometry-error and skyline tests.'))
report=dict(twigCandidates=rows,nearLeafExclusion=leaf,opaqueForestInvestigation=forests,totalProspectiveTwigTriangleSavings=sum(x['prospectiveTriangleSavings'] for x in rows),totalProspectiveTwigNativeByteSavings=sum(x['prospectiveNativeByteSavings'] for x in rows),referenceView='1280x720 ordinary60deg horizontal FOV, no VR warp, no FPS/GPU claim.')
Path(sys.argv[2]).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
