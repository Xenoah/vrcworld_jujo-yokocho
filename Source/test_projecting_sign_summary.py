"""Exercise only summary helpers; never execute the artifact-writing script."""
import ast,copy,hashlib,json,struct,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE=Path(__file__).with_name('write_validation_summary.py')
tree=ast.parse(SOURCE.read_text());env=dict(hashlib=hashlib,json=json,struct=struct)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cloth_use_wording','projecting_sign_metrics')],type_ignores=[]),str(SOURCE),'exec'),env)

class ProjectingSignSummaryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'Source').mkdir()
  payload=json.dumps(dict(materials=[{}]*110,images=[{}]*34)).encode();payload+=b' '*((-len(payload))%4)
  self.raw=b'glTF'+struct.pack('<III',2,len(payload)+20,len(payload))+b'JSON'+payload
  (self.root/'Source/TreeTopYokocho.glb').write_bytes(self.raw)
  self.manifest=dict(materials=[{}]*130,lights=[{}]*9)
  self.pin=dict(addedRows=[dict(triangles=7652,vertices=16290)],glbSha256=hashlib.sha256(self.raw).hexdigest(),nativeSha256='native')
  self.prior=dict(rows=[{}]*1107,manifest=copy.deepcopy(self.manifest))
  self.admission=dict(passed=True,oracleSha256='approved',addedBatches=1,scope=dict(passed=True,addedTriangles=7652,addedNativeVertices=16290,addedSourceVertices=16290))
  self.module=SimpleNamespace(validate_gate=lambda m:[],load_oracle=lambda root:self.pin,before=lambda root:self.prior,ORACLE_SHA256='approved',BEFORE_NATIVE_SHA256='prior')
 def run_metrics(self):
  with patch.dict(sys.modules,projecting_sign_contract=self.module):return env['projecting_sign_metrics'](self.root,self.manifest,self.admission)
 def test_historical_noren_wording_remains_exact(self):
  expected='閉じた店内の布張りは裏面カリング、単一面の街の布は両面描画。旧暖簾の設定は歴史的互換用で、現行の可視部品や節約量とは数えない'
  for f in ({},{'venue_projecting_signs':False},{'venue_projecting_signs':1}):self.assertEqual(env['cloth_use_wording'](f),expected)
  self.assertIn('Noren1/Noren3',env['cloth_use_wording']({'venue_projecting_signs':True}))
 def test_current_exact_metrics_distinguish_source_definitions_from_glb_use(self):
  result=self.run_metrics();self.assertEqual(result['native_material_definitions'],130);self.assertEqual(result['glb_used_materials'],110);self.assertEqual(result['glb_embedded_images'],34)
  self.assertEqual(result['projecting_sign_new_material_definitions'],0);self.assertEqual(result['projecting_sign_new_lights'],0);self.assertEqual(result['projecting_sign_added_triangles'],7652)
 def test_unfrozen_or_malformed_gate_is_not_reported_as_pass(self):
  self.module.validate_gate=lambda m:['invalid']
  with self.assertRaisesRegex(ValueError,'summary gate'):self.run_metrics()
  self.module.validate_gate=lambda m:[];self.module.load_oracle=lambda root:(_ for _ in ()).throw(ValueError('unfrozen'))
  with self.assertRaisesRegex(ValueError,'unfrozen'):self.run_metrics()
 def test_missing_failed_or_wrong_oracle_admission_rejected(self):
  for key,value in (('passed',False),('scope',{}),('oracleSha256','wrong')):
   with self.subTest(key=key):
    old=self.admission[key];self.admission[key]=value
    with self.assertRaisesRegex(ValueError,'native admission'):self.run_metrics()
    self.admission[key]=old
 def test_changed_counts_rejected(self):
  self.admission['scope']['addedTriangles']+=1
  with self.assertRaisesRegex(ValueError,'counters disagree'):self.run_metrics()
 def test_changed_glb_rejected(self):
  (self.root/'Source/TreeTopYokocho.glb').write_bytes(self.raw+b'x')
  with self.assertRaisesRegex(ValueError,'exact projecting-sign GLB'):self.run_metrics()

if __name__=='__main__':unittest.main(verbosity=2)
