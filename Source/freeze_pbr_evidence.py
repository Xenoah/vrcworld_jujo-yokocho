#!/usr/bin/env python3
"""Build exact candidate roster after independent generation and proof renders.
This only packages evidence. It cannot grant art admission or Unity validation.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}
def read(p):return json.loads((ROOT/p).read_text())
def write(p,data):(ROOT/p).write_text(json.dumps(data,indent=2)+'\n')
origin=read('Docs/authored_pbr_origin.json');oh=sha(ROOT/'Docs/authored_pbr_origin.json')
assert sha(ROOT/origin['sourcePath'])==origin['sourceSha256']
paths=[Path(m['path']) for f in origin['families'] for m in f['maps'].values()]
assert len(paths)==16
maps=[rec(ROOT/p) for p in paths];mapsha={p['sha256'] for p in maps}
for f in origin['families']:
 for m in f['maps'].values():assert sha(ROOT/m['path'])==m['sha256']
for file in ['Docs/authored_pbr_validation.json','Docs/multiscale_seam_validation.json']:
 d=read(file);assert d['originSha256']==oh
 assert (d.get('passed') is True or d.get('status')=='PASS'),file
repro=ROOT/'ReproductionFinal';checks=[]
for p in [Path('Source/author_seamless_pbr.py'),Path('Docs/authored_pbr_origin.json'),*paths,*[Path('Preview')/(f['family']+'_contact.png') for f in origin['families']]]:
 a,b=sha(ROOT/p),sha(repro/p);checks.append({'path':str(p),'original':a,'reproduced':b,'equal':a==b})
assert all(c['equal'] for c in checks)
write('Docs/procedural_reproducibility.json',{'schema':2,'status':'PASS','originSha256':oh,'scope':'Independent clean-directory rerun with recorded dependency versions. Byte equality, not art approval.','checkCount':len(checks),'mapsReproduced':16,'sourceReadOnlyImageInputs':[],'checks':checks})
# Require the full matched comparison set, not merely map statistics.
required=['material_studio_baseline','material_studio_authored','actual_rock_baseline','actual_rock_authored']
for mode in ['baseline','authored']:
 required += [f'actual_trunk_{mode}_{k}' for k in ['close','mid','grazing_left','grazing_right','dim_grazing_right']]
 required += [f'{f["family"]}_tile_{mode}' for f in origin['families']]
 required += [f'world_{mode}/Blender_{k}' for k in ['deck_walk','yakitori_service','alpine_city']]
for name in required:
 for suffix in ['.png','.json']:assert (ROOT/'Preview'/(name+suffix)).is_file(),name+suffix
bindings=[]
for p in sorted((ROOT/'Preview').rglob('*.json')):
 d=json.loads(p.read_text())
 if 'authored' not in str(p.relative_to(ROOT)):continue
 for key in ['originSha256','originalPbrOriginSha256']:
  if key in d:assert d[key]==oh,(str(p),key,d[key],oh)
 used=d.get('maps')
 if isinstance(used,dict):
  for key,v in used.items():
   if 'TreeTopYokochoOriginalPbr' in key:bindings.append({'proof':str(p.relative_to(ROOT)),'path':key,'sha256':v['sha256'],'current':v['sha256'] in mapsha})
 if isinstance(used,list):
  for v in used:bindings.append({'proof':str(p.relative_to(ROOT)),'path':v['path'],'sha256':v['sha256'],'current':v['sha256'] in mapsha})
 for v in d.get('overrides',[]):bindings.append({'proof':str(p.relative_to(ROOT)),'material':v[0],'slot':v[1],'path':v[2],'sha256':v[3],'current':v[3] in mapsha})
assert bindings and all(x['current'] for x in bindings)
proofs=[rec(p) for p in sorted((ROOT/'Preview').rglob('*')) if p.is_file() and p.suffix in ['.json','.png']]
write('Docs/proof_integrity.json',{'schema':1,'status':'PASS','originSha256':oh,'scope':'Proof file hashes and exact current-map bindings, not visual acceptance. Baseline renderer inputs stay historical.','requiredPairedRenders':len(required),'currentMapBindings':len(bindings),'bindings':bindings,'proofs':proofs,'renderSources':[rec(p) for p in sorted((ROOT/'Source').glob('render_*.py'))]})
(ROOT/'Docs/texture_sha256.txt').write_text(''.join(f"{x['sha256']}  {x['path']}\n" for x in maps))
write('Docs/texture_candidate_manifest.json',{'schema':2,'status':'FROZEN SOURCE/MAP EVIDENCE; ART ACCEPTANCE RECORDED SEPARATELY; NOT UNITY VALIDATION','source':rec(ROOT/origin['sourcePath']),'origin':rec(ROOT/'Docs/authored_pbr_origin.json'),'mapping':rec(ROOT/'Docs/material_slot_mapping.json'),'maps':maps,'validation':[rec(ROOT/p) for p in ['Docs/authored_pbr_validation.json','Docs/multiscale_seam_validation.json','Docs/procedural_reproducibility.json','Docs/proof_integrity.json']],'totalMapBytes':sum(x['bytes'] for x in maps),'sourceFiles':[rec(p) for p in sorted((ROOT/'Source').glob('*.py'))],'previewFiles':proofs,'supportingDocuments':[rec(ROOT/p) for p in ['Docs/MaterialStudy.md','Docs/REPRODUCE.md','Docs/VisualReview.md','Docs/portable_resolver_smoke.json','Docs/core_input_integrity.json']],'historicalRenderSources':[rec(p) for p in sorted((ROOT/'Docs/RenderSourceHistory').rglob('*')) if p.is_file()],'excludedDevelopmentDirectories':['Studies','Reproduction','ReproductionFinal']})
print(json.dumps({'status':'PASS; art acceptance recorded separately','originSha256':oh,'mapCount':len(maps),'reproductionChecks':len(checks),'pairedRenders':len(required),'proofBindings':len(bindings),'totalMapBytes':sum(x['bytes'] for x in maps)},indent=2))
