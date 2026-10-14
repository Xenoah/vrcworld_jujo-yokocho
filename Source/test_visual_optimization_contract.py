"""Independent mutation tests for approved optimization pins; no baseline edits."""
import copy,gzip,hashlib,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import peer_culling_contract as peer
import visual_optimization_contract as contract
import noren_payload_contract as noren

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
DATA=ROOT/'Assets/TreeTopYokocho/Data'
manifest=json.loads((DATA/'WorldManifest.json').read_text());baseline=peer.load_baseline(ROOT)
actual=peer.read_visual(DATA/'VisualMeshes.bytes');summaries=[peer.summarize(x) for x in actual];oracle=contract.load_oracle(ROOT)
assertions=0
# Current bytes stay distinct from TEST-ONLY restored legacy synthetic rows.
current_manifest=copy.deepcopy(manifest);current_actual=actual
if manifest.get('features',{}).get('shop_personality') is True:
 from shop_personality_test_fixture import restore_prior_shops
 ok,detail=peer.validate_peer_culling(ROOT,current_manifest);assert ok,detail;assertions+=1
 actual,manifest=restore_prior_shops(actual,manifest);summaries=[peer.summarize(x) for x in actual]

def counted(rows,m):
 m=dict(m);m['visualMeshCount']=len(rows);m['visualTriangles']=sum(r['triangles'] for r in rows);return m

def expect(rows,m,wanted,reason=None):
 global assertions
 assertions+=1;ok,detail=peer.validate_summaries(rows,counted(rows,m),baseline)
 assert ok==wanted,(assertions,detail)
 if reason:assert any(x['reason']==reason for x in detail['errors']),(reason,detail)

expect(summaries,manifest,True)
# Each of four independent enable/disable combinations admits exactly its
# pinned after rows and requires the corresponding before rows otherwise.
for unused in [False,True]:
 for sea in [False,True]:
  m=copy.deepcopy(manifest);m['features'].update(visual_unused_compaction=unused,static_planar_sea=sea)
  lookup={(r['before']['group'],r['before']['material']):r for r in oracle['changes']};rows=[]
  for r in summaries:
   pin=lookup.get((r['group'],r['material']))
   rows.append(copy.deepcopy((pin['after'] if (sea if pin['kind']=='static-planar-sea' else unused) else pin['before']) if pin else r))
  expect(rows,m,True)
for flag in contract.FEATURES:
 for value in [None,False,0,1,1.0,'true','True',{},[],np.bool_(True)]:
  m=copy.deepcopy(manifest);m['features'][flag]=value
  expect(summaries,m,False,'Exact visual optimization payload mismatch')
 # Omitted flag is disabled too.
 m=copy.deepcopy(manifest);del m['features'][flag];expect(summaries,m,False,'Exact visual optimization payload mismatch')
for pin in oracle['changes']:
 key=(pin['after']['group'],pin['after']['material']);i=next(i for i,r in enumerate(summaries) if (r['group'],r['material'])==key)
 for field in contract.FIELDS:
  rows=copy.deepcopy(summaries);rows[i][field]=rows[i][field]+1 if isinstance(rows[i][field],int) else '0'*64
  expect(rows,manifest,False,'Exact visual optimization payload mismatch')
 for mode in ['missing','duplicate','rename']:
  rows=copy.deepcopy(summaries)
  if mode=='missing':rows.pop(i)
  if mode=='duplicate':rows.append(copy.deepcopy(rows[i]))
  if mode=='rename':rows[i]['group']+='_Far'
  expect(rows,manifest,False,'Optimization batch missing or duplicated')
# Identity was NOT compacted; all existing107 exact indexed component slices
# remain tested on exact historical bytes when the new shop feature replaces
# them. Current shop-native admission above is separate and not an inverse.
slices_ok,slices=noren.validate_native_slices(actual);assert slices_ok and slices['exactPreservedNorenComponentSlices']==107;assertions+=1
# Summary-only altered count cannot be hidden by the internal normalization.
bad=copy.deepcopy(manifest);bad['visualTriangles']+=1
ok,detail=peer.validate_summaries(summaries,bad,baseline);assert not ok and any(e['reason']=='Manifest export count mismatch' for e in detail['errors']);assertions+=1
# Oracle tamper is detected before exact after pins can be substituted.
original=Path.read_bytes
with patch.object(Path,'read_bytes',lambda p:original(p)+b' ' if p.name==contract.ORACLE_NAME else original(p)):
 try:contract.load_oracle(ROOT)
 except ValueError:assertions+=1
 else:raise AssertionError('Oracle corruption admitted')
# Shard-only reconstruction: use actual deterministic transport bytes and an
# independently reassembled temp native file; no existing raw path is read by
# the admission call. Includes per-shard, combined and raw checksums.
from visual_transport import read_visual_transport
raw=(DATA/'VisualMeshes.bytes').read_bytes();transport_raw=read_visual_transport(DATA)
with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'from_shards.bytes';path.write_bytes(transport_raw);assert path.read_bytes()==raw
 ok,detail=peer.validate_peer_culling(ROOT,current_manifest,path);assert ok,detail;assertions+=1
 # Actual native wrong attribute/hash cannot be normalized. Mutate last
 # byte of a known changed batch's UV using in-memory native adapter only.
 changed=list(current_actual);idx=next(i for i,b in enumerate(current_actual) if (b['group'],b['material'])==tuple(contract.SEA_KEYS[0]));b=dict(current_actual[idx]);b['uv']=b['uv'].copy();b['uv'][0,0]+=1;changed[idx]=b
 with patch.object(peer,'read_visual',return_value=changed):
  ok,detail=peer.validate_peer_culling(ROOT,current_manifest,path);assert not ok;assertions+=1
# Both summary metadata and actual shader bytes are independently required.
bad=copy.deepcopy(manifest);bad['meshOptimization']['sea']['waterShaderSha256']='0'*64
expect(summaries,bad,False,'Static planar sea shader profile mismatch')
original=Path.read_bytes
contract.verified_static_sea_shader(ROOT);assertions+=1
with patch.object(Path,'read_bytes',lambda p:original(p)+b' ' if p.name=='YokochoWater.shader' else original(p)):
 # Preserve the old Water-specific guard independently of an earlier outer
 # source guard. Both must reject the actual same shader-byte mutation.
 try:contract.verified_static_sea_shader(ROOT)
 except ValueError as error:
  assert 'non-displacing Water shader' in str(error);assertions+=1
 else:raise AssertionError('Direct static Water guard admitted shader mutation')
 ok,detail=peer.validate_peer_culling(ROOT,current_manifest)
 expected_error='YokochoWater.shader' if (ROOT/'Assets/TreeTopYokocho/Editor/VenueLightingProfile.cs').is_file() else 'non-displacing Water shader'
 assert not ok and expected_error in detail['error'];assertions+=1
for value in [None,[],1,'true']:
 bad=dict(current_manifest);bad['features']=value
 ok,detail=peer.validate_peer_culling(ROOT,bad);assert not ok;assertions+=1
 for layer in ['meshOptimization','sea']:
  bad=copy.deepcopy(manifest)
  if layer=='meshOptimization':bad[layer]=value
  else:bad['meshOptimization'][layer]=value
  expect(summaries,bad,False,'Static planar sea shader profile mismatch')
print(json.dumps(dict(status='PASS',assertions=assertions,exactRows=len(oracle['changes']),historicalNorenSlices=107,currentNativeShopReplacement=current_manifest.get('features',{}).get('shop_personality') is True,summaryOnly=True,shardOnlyReconstruction=True,oracleSha256=contract.ORACLE_SHA256),indent=2))
