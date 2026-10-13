"""Integrated altitude, cloud and service-prop checks. No Unity execution."""
from pathlib import Path
import json,sys,math
import numpy as np
from validate_crown import read_collision
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
m=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
expected={'G0':0,'L1':134,'L2':140,'L3':146,'L4':152}
levels={x['level']:x['z'] for x in m['floors']}
check('Actual floor metadata has raised decks and fixed ground',levels==expected,levels)
check('All four player spawns are on the raised arrival deck',all(abs(x['position'][2]-134.08)<1e-5 for x in m['spawns']))
check('Every seat and exit moved with its shop',min(x['position'][2] for x in m['stations'])>134 and min(x['exit'][2] for x in m['stations'])>134)
visual=read_collision(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
collision=read_collision(root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes')
cloud=np.concatenate([x['triangles'].reshape(-1,3) for x in visual if x['group'].startswith('Landscape/CloudSea_')])
# Only the explicit cloud-depth flag permits the separately reviewed lower
# cloud envelope. The eight exact replacement payload hashes are gated by the
# peer contract separately; no other protected geometry tolerance is changed.
cloud_depth=m.get('features',{}).get('cloud_depth') is True
cloud_lower=93.2 if cloud_depth else 110.0
check('Actual cloud mesh stays inside the explicitly selected cloud envelope',cloud[:,2].min()>=cloud_lower and cloud[:,2].max()<124,[float(cloud[:,2].min()),float(cloud[:,2].max())])
check('Cloud altitude metadata matches actual exported bounds',m['cloudSea']['altitudeBounds']==[round(float(cloud[:,2].min()),3),round(float(cloud[:,2].max()),3)])
check('Maximum permitted cloud swell stays below124m',float(cloud[:,2].max())+.15<124)
cloud_material=[x for x in m['materials'] if x['name']=='CloudSeaSilver']
check('Descriptive cloud base follows the selected envelope',len(cloud_material)==1 and cloud_material[0].get('cloudBaseZ')==cloud_lower)
if cloud_depth:
    d=m['cloudSea'].get('depthRefinement',{})
    check('Cloud depth is the explicit reviewed Z-only profile',d.get('id')=='CloudShoulders_ZOnly_2p2_About124m' and d.get('axis')=='Z' and d.get('anchorZ')==124.0 and d.get('factor')==2.2 and d.get('altitudeEnvelope')==[93.2,124.0] and d.get('maximumShaderSwell')==.15)
else:
    check('Legacy cloud profile remains unchanged without literal opt-in','depthRefinement' not in m['cloudSea'])
check('Lowest public alley is at least10m above maximum animated clouds',levels['L1']-m['cloudSea']['maximumAnimatedAltitude']>=10)
check('Clouds do not create floor or barrier colliders',not any('CloudSea' in x['group'] for x in collision))
check('Cloud layer stays within source draw and triangle budget',m['cloudSea']['drawBatches']<=8 and m['cloudSea']['triangles']<=40000)
peer=np.concatenate([x['triangles'].reshape(-1,3) for x in visual if x['group'].startswith('Landscape/AncientPeers_')])
check('Peer giant-tree geometry rises above the cloud sea',peer[:,2].max()>165,float(peer[:,2].max()))
p=m['boosterPumps'];stats=p['stats']
check('Three staged pumping elevations and upper storage',len(p['stations'])==3 and [x['toZ'] for x in p['pressureZones']]==[52,102,155] and p['storage']['deckZ']==155)
check('Upper storage ties into raised water supply',abs(p['storage']['riserConnection'][2]-152)<1e-6)
check('Pumping props have bounded geometry and no new textures',stats['triangles']<=24000 and stats['newTextures']==0,stats)
check('No unsupported physical certification claimed',p['engineeringCertified'] is False)
check('Actual booster mesh is present',any(x['group'].startswith('Infrastructure/Boosters/') for x in visual))
check('Leaf-defined near crowns replace opaque cores',m['detail']['leafDefinedCrowns']>=700 and m['detail']['removedNearCoreTriangles']>70000,m['detail']['leafDefinedCrowns'])
builder=(root/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
check('Unity reflection-probe locations follow raised alley',all(x in builder for x in ['manifest.altitudeProfile.addedAlleyHeight','locations[i].y += alleyLift']))
check('Cloud renderer avoids static GI and shadow/probe cost',all(x in builder for x in ['bool animated = foliage || beacon || cloud','renderer.receiveShadows = !cloud','beacon || cloud ? LightProbeUsage.Off']))
# Use actual float32 wall solids, not only their emitted front-ray metadata.
from shapely.geometry import MultiPoint
joint_mesh=next(x for x in collision if x['group']=='Safety/Crown/LookoutCornerClosure')
joint=MultiPoint(joint_mesh['vertices'][:,:2]).convex_hull
contacts={}
for prefix in ['Safety/L4','Safety/Crown/CrownLookoutBridge/']:
 solids=[MultiPoint(tri.reshape(-1,3)[:,:2]).convex_hull for mesh in collision if mesh['group'].startswith(prefix) for tri in mesh['triangles'].reshape(-1,12,3,3)]
 contacts[prefix]=min(joint.distance(poly) for poly in solids)
check('L4 lookout joint overlaps both actual barrier solids',all(d<1e-6 for d in contacts.values()),contacts)
report=dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',scope='Actual exported source geometry, metadata and builder source; Unity/VRChat shaders, physics and performance remain untested.',checks=checks)
(root/'Docs/altitude_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(report['status']!='PASS')
