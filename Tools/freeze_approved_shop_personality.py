"""One-time integrator operation after independent visual acceptance.

Requires externally supplied approved native and editable GLB SHAs; never approves a
candidate, refreshes the before evidence, or modifies the requested project.
Outputs a separate oracle plus a suggested constant for selective integration.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Source'))
parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True);parser.add_argument('--approved-native-sha',required=True);parser.add_argument('--approved-glb-sha',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
sys.path.append(str(args.project/'Source'))
import shop_personality_contract as c
from audit_shop_personality_scope import audit
from peer_culling_contract import read_visual,summarize
raw=(args.project/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes();sha=hashlib.sha256(raw).hexdigest()
if sha!=args.approved_native_sha:raise SystemExit('Input is not the independently approved native artifact')
glb_sha=hashlib.sha256((args.project/'Source/TreeTopYokocho.glb').read_bytes()).hexdigest()
if glb_sha!=args.approved_glb_sha:raise SystemExit('Input is not the independently approved editable GLB artifact')
report=audit(args.project)
if report['errors'] or report['scope']!='proposal':raise SystemExit('Scope must pass on a complete proposal before freezing: '+str(report['errors']))
manifest=json.loads((args.project/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text());before=c.load_before();nonshop={c.key(r) for r in before['rows'] if c.key(r) not in set(map(tuple,before['shopKeys']))};rows=[summarize(b) for b in read_visual(args.project/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')]
# Capture provenance must describe the actual source files being frozen, not
# merely preserve two contradictory hashes in the same approved oracle.
for shop in manifest['shopPersonality']['shops']:
 expected='nightlife_venues' if shop['id'] in c.NIGHTLIFE else 'food_venues'
 if shop.get('module')!=expected:raise SystemExit('Shop module differs from exact five-food/three-nightlife ownership: '+shop['id'])
 source=args.project/'Source'/(expected+'.py')
 if shop.get('sourceSha256')!=hashlib.sha256(source.read_bytes()).hexdigest():raise SystemExit('Shop declared source provenance does not match actual module file: '+shop['id'])
new_files={}
for p in sorted((args.project/'Assets/TreeTopYokocho/Textures').rglob('*')):
 if not p.is_file() or p.suffix=='.meta':continue
 rel=str(p.relative_to(args.project))
 if rel not in before['dependencies']:
  if not p.name.startswith(('food_venue_','nightlife_')):raise SystemExit('New unrelated texture not authorized: '+rel)
  new_files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('food_venues','nightlife_venues','shop_personality','build_world'):
 p=args.project/'Source'/(name+'.py');new_files[str(p.relative_to(args.project))]=hashlib.sha256(p.read_bytes()).hexdigest()
for rel in ('Source/shop_personality_legacy_materials.json','Assets/TreeTopYokocho/Data/FantasyMaterials.json'):
 p=args.project/rel;new_files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(schema=1,version=c.VERSION,beforeNativeSha256=c.BEFORE_NATIVE_SHA256,approvedNativeSha256=sha,approvedGlbSha256=glb_sha,
            shopRows=[r for r in rows if c.key(r) not in nonshop],nativeKeyOrder=[list(c.key(r)) for r in rows],
            manifestFieldHashes={k:c.digest(v) for k,v in manifest.items()},dependencies=new_files,
            scope='Exact approved shop architecture plus immutable whole-world complement. This capture is not itself visual approval.')
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(output=str(args.output),oracleSha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),approvedNativeSha256=sha,approvedGlbSha256=glb_sha,shopBatches=len(result['shopRows']),nonshopBatches=len(nonshop),note='Set ORACLE_SHA256 only after independent reviewer checks this exact artifact and oracle.'),indent=2))
