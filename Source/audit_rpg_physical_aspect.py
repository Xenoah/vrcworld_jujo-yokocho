import sys,json,hashlib
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(root/'Source'))
from test_rpg_shop_identities import make
import rpg_shop_identities as rpg
rows=[]
for idx in range(8):
 old,_=make(idx,False);new,_=make(idx,True);r=rpg.name_rect(idx);uvrect=rpg.uv(r);ratios=[];count=0
 for key,b in new.batches.items():
  if key[1] not in ('Food_Sign','Night_Print'):continue
  v=np.array(b['v']);u=np.array(b['uv']);f=np.array(b['f'])
  for tri in f:
   U=u[tri]
   if not (np.all(U[:,0]>=uvrect[0]-1e-8) and np.all(U[:,0]<=uvrect[2]+1e-8) and np.all(U[:,1]>=uvrect[1]-1e-8) and np.all(U[:,1]<=uvrect[3]+1e-8)):continue
   du=(U[1:]-U[0])*2048
   if abs(np.linalg.det(du))<1e-12:continue
   dv=v[tri[1:]]-v[tri[0]]
   jac=np.linalg.solve(du,dv);s=np.linalg.svd(jac,compute_uv=False)
   ratio=float(max(s)/min(s));ratios.append(ratio);count+=1
 if not ratios:raise AssertionError('No principal sign face '+str(idx))
 if max(ratios)>1.004:raise AssertionError((idx,max(ratios)))
 _,info=rpg._sign(idx,(r[2]-r[0],r[3]-r[1]))
 rows.append(dict(shop=f'S{idx+1:02d}',name=rpg.IDENTITIES[idx]['name'],actualProductionTriangles=count,maxWorldToTexelAnisotropy=max(ratios),titleInkBounds=info['inkBounds'],pixelWindow=r))
out=dict(method='Singular-value ratio of world-space / 2048-pixel UV Jacobian on actual principal-sign triangles; 1 means isotropic. Less than 0.4% deviation allowed for integer raster window rounding.',passed=True,shops=rows)
output_dir=root/'Preview/rpg-sign-model-proofs'
output_dir.mkdir(parents=True,exist_ok=True)
(output_dir/'physical-aspect-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
