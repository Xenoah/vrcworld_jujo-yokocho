import sys,json,numpy as np
from collections import defaultdict
from peer_culling_contract import read_visual
batches=read_visual(sys.argv[1]);families=defaultdict(lambda:dict(vertices=0,triangles=0,unusedVertices=0,axisPlanarTriangles=0))
rows=[]
for b in batches:
 v,f=b['vertices'],b['faces'];q=v[f];planar=np.any(np.ptp(q,axis=1)==0,axis=1);unused=len(v)-len(np.unique(f));group=b['group'];family='/'.join(group.split('/')[:2]);d=families[family]
 for k,x in [('vertices',len(v)),('triangles',len(f)),('unusedVertices',unused),('axisPlanarTriangles',int(planar.sum()))]:d[k]+=x
 rows.append(dict(group=group,material=b['material'],vertices=len(v),triangles=len(f),unusedVertices=unused,axisPlanarTriangles=int(planar.sum())))
report=dict(families=sorted([dict(family=k,**v) for k,v in families.items()],key=lambda x:-x['triangles']),batches=sorted(rows,key=lambda x:-x['triangles']))
print(json.dumps(report,indent=2))
