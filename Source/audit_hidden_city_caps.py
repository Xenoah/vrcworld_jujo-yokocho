"""Read-only proof of city-bracket top caps enclosed by opaque fascia boxes."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Source'))
from peer_culling_contract import read_visual
path=Path(sys.argv[1]);b=next(x for x in read_visual(path) if (x['group'],x['material'])==('Landscape/DetailCityRoofs','DarkTimber'));v=b['vertices'].astype(float);f=b['faces'];assert len(v)==30024 and len(f)==15012
boxes=v.reshape(-1,24,3);assert len(boxes)==139*9
# Independently verify plain-box ordered topology. No disconnected/coplanar
# reinterpretation, no mutation and no deletion of mesh arrays happens here.
base=np.array([[4*j,4*j+1,4*j+2] for j in range(6)]+[[4*j,4*j+2,4*j+3] for j in range(6)])
expected=[]
for j in range(6):expected.extend([[4*j,4*j+1,4*j+2],[4*j,4*j+2,4*j+3]])
assert all(np.array_equal(f[i*12:(i+1)*12]-i*24,expected) for i in range(len(boxes)))
rows=[]
for house in range(139):
 for side in range(2):
  fascia_index=house*9+side;fascia=boxes[fascia_index];origin=fascia[0];basis=np.column_stack([fascia[3]-origin,fascia[1]-origin,fascia[4]-origin]);lengths=np.linalg.norm(basis,axis=0)
  for j in range(3):
   bracket_index=house*9+3+side*3+j;bracket=boxes[bracket_index];cap=bracket[4:8];assert np.ptp(cap[:,2])<1e-9 and cap[0,2]>bracket[:4,2].max()
   local=np.linalg.solve(basis,(cap-origin).T).T
   clearance=float(np.min(np.minimum(local,1-local)*lengths[None,:]));assert clearance>0
   # Every cap corner is strictly inside an oriented convex fascia box.
   # Consequently the entire two-triangle cap lies inside by convexity.
   rows.append(dict(house=house,fasciaBox=fascia_index,bracketBox=bracket_index,capTriangles=[bracket_index*12+2,bracket_index*12+3],capVertexRange=[bracket_index*24+4,bracket_index*24+8],minimumEnclosureClearanceMetres=clearance))
report=dict(status='AUDIT_ONLY_NO_GEOMETRY_CHANGE',nativeSha256=hashlib.sha256(path.read_bytes()).hexdigest(),batch=[b['group'],b['material']],houses=139,brackets=834,enclosedTopCaps=len(rows),prospectiveRemovedTriangles=len(rows)*2,prospectiveRemovableVertices=len(rows)*4,prospectiveNativeByteReduction=len(rows)*(2*12+4*24),minimumEnclosureClearanceMetres=min(r['minimumEnclosureClearanceMetres'] for r in rows),normals='Each box face owns separate four vertices; side-face normals/UVs/colors/order need not change if isolated top-cap triangles and now-unused cap vertices are omitted. Current exporter remains untouched.',restrictions='Needs explicit protected-batch revision, independent ordered-surviving-corner and bounds tests, opaque static fascia dependency, and external-view/shadow review. Not an implemented optimization or measured GPU result.',caps=rows)
Path(sys.argv[2]).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='caps'},indent=2))
