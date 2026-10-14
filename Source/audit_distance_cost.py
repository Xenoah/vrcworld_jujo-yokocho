"""Read-only native cost and route-sample distance audit. Does not change meshes."""
import sys,json,hashlib,re,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Source'))
from peer_culling_contract import read_visual
root=Path(sys.argv[1]);out=Path(sys.argv[2]);data=root/'Assets/TreeTopYokocho/Data';manifest=json.loads((data/'WorldManifest.json').read_text());batches=read_visual(data/'VisualMeshes.bytes')
eyes=np.asarray([r['position'] for r in manifest['floorTests']])+[0,0,1.65];tree=cKDTree(eyes)

def family(group,material):
 if group.startswith('Tree/Crown_'):return 'Host crown / '+('folded leaves' if re.fullmatch('Foliage[0-3]',material) else material)
 if group.startswith('Tree/Framing_'):return 'Host framing / '+('folded leaves' if re.fullmatch('Foliage[0-3]',material) else material)
 if group.startswith('Landscape/ForestGrove_'):return 'Forest groves / '+('opaque canopy' if material.startswith('ForestCanopy') else material)
 if group.startswith('Landscape/AncientPeers_'):return 'Ancient peers / '+('opaque canopy' if material.startswith('ForestCanopy') else material)
 if group.startswith('Landscape/DetailLeaves_'):return 'Scenery sprays / '+('peers' if '_Peer_' in group else 'groves')
 if group.startswith('Landscape/DetailTwigs_'):return 'Scenery twigs / '+('peers' if '_Peer_' in group else 'groves')
 if group.startswith('Shops/'):return 'Near shops / '+('bottles' if material.startswith('Bottle') else material)
 if group.startswith('Railings/'):return 'Near railings / '+material
 if group.startswith('Landscape/DetailCity'):return 'Distant city detail / '+material
 if group.startswith('Landscape/FortifiedCity'):return 'Distant city base / '+material
 if group.startswith('Landscape/Mainland_'):return 'Mainland terrain'
 if group.startswith('Landscape/SnowRange_'):return 'Snow range / '+material
 if group.startswith('Landscape/CloudSea_'):return 'Cloud sea'
 return '/'.join(group.split('/')[:2])+' / '+material

rows=[];parts=[]
for b in batches:
 g,m=b['group'],b['material'];v,f=b['vertices'],b['faces'];distance,eye=tree.query(v);idx=int(np.argmin(distance));fam=family(g,m)
 lo=v.min(axis=0);hi=v.max(axis=0);to_box=np.maximum(np.maximum(lo-eyes,eyes-hi),0);lower=float(np.linalg.norm(to_box,axis=1).min())
 rows.append(dict(group=g,material=m,family=fam,vertices=len(v),triangles=len(f),nativeAttributeIndexBytes=len(v)*24+len(f)*12,nearestRouteSampleVertexDistance=float(distance[idx]),nearestRouteSampleAabbLowerBound=lower,nearestEye=eyes[eye[idx]].tolist(),nearestFloorSample=manifest['floorTests'][eye[idx]],nearestVertex=v[idx].tolist(),bounds=[lo.tolist(),hi.tolist()]))
 # Exact-position connected components are diagnostic only. No vertices are
 # welded in any export, and material/group boundaries remain separated.
 selected=(g.startswith(('Landscape/ForestGrove_','Landscape/AncientPeers_','Landscape/DetailTwigs_','Tree/Crown_','Tree/Framing_','LanternStrings','Landscape/DetailCity')) or (g.startswith('Shops/') and m.startswith('Bottle')))
 if not selected:continue
 unique,inv=np.unique(v,axis=0,return_inverse=True);faces=inv[f];edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]));graph=coo_matrix((np.ones(len(edges),np.uint8),(edges[:,0],edges[:,1])),shape=(len(unique),len(unique)));n,labels=connected_components(graph,directed=False)
 used_labels=labels[faces[:,0]]
 for label in np.unique(used_labels):
  face_ids=np.flatnonzero(used_labels==label);vertex_ids=np.unique(f[face_ids]);p=v[vertex_ids];pl=p.min(axis=0);ph=p.max(axis=0);center=(pl+ph)/2;radius=float(np.linalg.norm(ph-pl)/2);d,ei=tree.query(center);lower=max(0,float(d)-radius);dv,ev=tree.query(p);nearest=int(np.argmin(dv))
  parts.append(dict(group=g,material=m,family=fam,triangles=len(face_ids),vertices=len(vertex_ids),center=center.tolist(),extent=(ph-pl).tolist(),boundingRadius=radius,nearestSampleVertexDistance=float(dv[nearest]),nearestSampleSphereLowerBound=lower,nearestSampleIndex=int(ev[nearest]),referenceProjectedDiameterPixels=1280/(2*math.tan(math.radians(30)))*(2*radius)/max(float(d)-radius,1e-6)))

families=defaultdict(lambda:dict(vertices=0,triangles=0,nativeAttributeIndexBytes=0,batches=0,nearestRouteSampleVertexDistance=float('inf')))
for r in rows:
 d=families[r['family']]
 for k in ['vertices','triangles','nativeAttributeIndexBytes']:d[k]+=r[k]
 d['batches']+=1;d['nearestRouteSampleVertexDistance']=min(d['nearestRouteSampleVertexDistance'],r['nearestRouteSampleVertexDistance'])
report=dict(inputNativeSha256=hashlib.sha256((data/'VisualMeshes.bytes').read_bytes()).hexdigest(),inputManifestSha256=hashlib.sha256((data/'WorldManifest.json').read_bytes()).hexdigest(),routeEyeSamples=len(eyes),scope='Distances are to authored floor-probe eye samples, not visibility/raycast/continuous-route guarantees. Shoulder samples included conservatively. AABB/sphere values are lower bounds for sampled eyes; closest vertex is only a measured upper bound for surface distance. Pixel diameter is on-axis1280px60HFOV reference, not runtime cost.',families=sorted([dict(family=k,**v) for k,v in families.items()],key=lambda x:-x['triangles']),batches=rows,components=parts)
out.write_text(json.dumps(report,indent=2));print(json.dumps(dict(batches=len(rows),components=len(parts),families=report['families'][:18]),indent=2))
