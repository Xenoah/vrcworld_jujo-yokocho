"""Capture a compact scope-checked proposal; never self-approve or set a pin."""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Source'))
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.append(str(a.project/'Source'))
import projecting_sign_contract as c
import s05_pendant_contract as prior
from audit_projecting_sign_scope import audit
from audit_projecting_sign_glb import audit as glb_audit
from peer_culling_contract import read_visual
from rpg_identity_contract import summarize_batches
report=audit(a.project);glb=glb_audit(a.project)
(ROOT/'Docs/projecting-sign-proposal-scope.json').write_text(json.dumps(dict(native=report,glb=glb),indent=2)+'\n')
if report['errors'] or glb['errors']:raise ValueError('Proposal scope failed; see projecting-sign-proposal-scope.json')
rows=summarize_batches(read_visual(a.project/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'));summary=[{f:r[f] for f in c.FIELDS} for r in rows];m=json.loads((a.project/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
deps={rel:c.sha((a.project/rel).read_bytes()) for rel in tuple(prior.load_oracle()['dependencies'])+c.NEW_SOURCES}
result=dict(schema=1,version=c.VERSION,beforeNativeSha256=c.BEFORE_NATIVE_SHA256,beforeOracleSha256=c.BEFORE_ORACLE_SHA256,addedKeys=[list(k) for k in c.KEYS],rows=summary,addedRows=[r for r in rows if c.key(r) in set(c.KEYS)],rowsSha256=c.digest(summary),arrayRowsSha256=c.digest(rows),manifestFieldHashes={k:c.digest(v) for k,v in m.items()},manifestFieldOrder=sorted(m,key=lambda k:(len(c.encoded(m[k])),k)),nativeSha256=report['actualNativeSha256'],glbSha256=glb['glbSha256'],collisionSha256=c.sha((a.project/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes()),dependencies=deps)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(gzip.compress(c.encoded(result),mtime=0))
print(json.dumps(dict(proposalOnly=True,proposalSha256=c.sha(a.output.read_bytes()),nativeSha256=result['nativeSha256'],glbSha256=result['glbSha256'],bytes=a.output.stat().st_size),indent=2))
