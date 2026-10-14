"""Independent source-triangle cloth density and closed-orientation measurement."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Source'))
from test_venue_projecting_signs import make

def quantile(values,weights,q):
 order=np.argsort(values);v=np.array(values)[order];w=np.array(weights)[order];return float(np.interp(q,np.cumsum(w)/sum(w),v))
rows=[]
for idx in (1,3,7):
 g,m,*_=make(idx)
 comp=next(c for c in m['parts'][0]['components'] if c['semantic']=='GuildPennant')
 cloth=next(r for r in comp['ranges'] if r['key'][1] not in ('Iron','Bronze'))
 batch=g.batches[tuple(cloth['key'])];va=cloth['vertexStart'];vb=va+cloth['vertexCount'];fa=cloth['triangleStart'];fb=fa+cloth['triangleCount']
 vv=np.array(batch['v'])[va:vb];uv=np.array(batch['uv'])[va:vb];ff=np.array(batch['f'])[fa:fb]-va
 mesh=trimesh.Trimesh(vv,ff,process=True)
 q=vv[ff];u=uv[ff];normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);area=np.linalg.norm(normal,axis=1)/2
 e=np.stack([q[:,1]-q[:,0],q[:,2]-q[:,0]],axis=2);du=np.stack([u[:,1]-u[:,0],u[:,2]-u[:,0]],axis=2)
 j=du@np.linalg.pinv(e);norm=np.linalg.norm(j,axis=2)
 # Broad cloth / loop faces; transparent exclusion of near-degenerate side UVs.
 keep=(norm.min(axis=1)>1e-8)&(np.abs(normal[:,1])>np.linalg.norm(normal,axis=1)*.75)&(area>1e-7)
 density=96*norm[keep];period=1000/density
 rows.append(dict(shop=m['shop'],material=cloth['key'][1],clothTriangles=len(ff),
  actualClosed=bool(mesh.is_watertight),outwardVolumeM3=float(mesh.volume),windingConsistent=bool(mesh.is_winding_consistent),
  sampledTriangles=int(keep.sum()),sampledAreaM2=float(area[keep].sum()),totalAreaM2=float(area.sum()),
  uvRepeatsPerMetreQuantiles=[[quantile(norm[keep,k],area[keep],p) for p in (.1,.5,.9)] for k in (0,1)],
  proceduralWeave96PeriodMmQuantiles=[[quantile(period[:,k],area[keep],p) for p in (.1,.5,.9)] for k in (0,1)],
  runtimeShader='Cloth', proceduralWeaveEnabled=idx!=3, runtimeWeaveStrength=0 if idx==3 else .045,
  runtimeNote='Noren1/3 retain Cloth with fixed weave96. Night_WineUpholstery retains Cloth routing with _WeaveStrength=0, so its 96-cycle period is a theoretical UV diagnostic only; no runtime visibility claim'))
 for key in ('actualClosed','windingConsistent'):assert rows[-1][key]
 assert rows[-1]['outwardVolumeM3']>0
out=dict(sourceSha256=hashlib.sha256((ROOT/'Source/venue_projecting_signs.py').read_bytes()).hexdigest(),scope='actual new cloth triangle arrays and UVs; no shader/profile/descriptor change',rows=rows)
(ROOT/'Docs/cloth-uv-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
