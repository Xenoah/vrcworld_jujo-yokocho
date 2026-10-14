"""Execute the real owner hook in isolation; no world build or render."""
import ast,copy,hashlib,os,pickle,random
from pathlib import Path
import unittest
from types import SimpleNamespace
import numpy as np

ROOT=Path(os.environ.get('YOKOCHO_SOURCE_ROOT',Path(__file__).resolve().parents[1]))
SOURCE=ROOT/'Source/build_world.py'

def extracted_hook():
 tree=ast.parse(SOURCE.read_text());loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [getattr(x,'id',None) for x in n.target.elts]==['idx','s'])
 branch=next(n for n in loop.body if isinstance(n,ast.If));first=next(i for i,n in enumerate(branch.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='signs_before' for t in n.targets));last=next(i for i,n in enumerate(branch.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='projecting_sign_records')
 return compile(ast.fix_missing_locations(ast.Module(body=branch.body[first:last+1],type_ignores=[])),str(SOURCE),'exec')

def fingerprints(g):return {k:hashlib.sha256(pickle.dumps(v,protocol=4)).hexdigest() for k,v in g.batches.items()}

class ProjectingSignSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.hook=extracted_hook();cls.tree=ast.parse(SOURCE.read_text())
 def environment(self,action=None):
  g=SimpleNamespace(batches={('Old/Exact','Timber'):{'v':[[0,0,0]],'f':[],'uv':[[0,0]]}},materials={'Timber':{'name':'Timber','color':[1,1,1]}},group='Shops/S01')
  env=dict(g=g,s={'id':'S01'},idx=0,M={'wood':'Timber'},w=6.,dep=5.4,P=lambda *x:x,rng=np.random.default_rng(31),random=random,np=np,copy=copy,pickle=pickle,batch_fingerprints=fingerprints,projecting_sign_records=[])
  def add_signs(g,P,idx,M,w,dep):
   g.batches[('Shops/S01/ProjectingSigns/Emblem','Timber')]={'v':[[0,0,2.4]],'f':[],'uv':[[0,0]]}
   if action:action(env)
   return env.get('result',{'shop':'S01'})
  env['add_signs']=add_signs;return env
 def test_exact_addition_keeps_old_state(self):
  env=self.environment();before=copy.deepcopy(env['g'].batches[('Old/Exact','Timber')]);exec(self.hook,env);self.assertEqual(env['projecting_sign_records'],[{'shop':'S01'}]);self.assertEqual(before,env['g'].batches[('Old/Exact','Timber')])
 def test_existing_geometry_or_identity_mutation_rejected(self):
  for action in (lambda e:e['g'].batches[('Old/Exact','Timber')]['v'][0].__setitem__(0,1),lambda e:e['g'].batches.pop(('Old/Exact','Timber'))):
   with self.assertRaisesRegex(ValueError,'existing batch'):exec(self.hook,self.environment(action))
 def test_added_namespace_escape_rejected(self):
  def action(e):e['g'].batches[('Shops/S02/ProjectingSigns/Emblem','Timber')]={}
  with self.assertRaisesRegex(ValueError,'owned namespace'):exec(self.hook,self.environment(action))
 def test_shared_material_mapping_or_group_mutation_rejected(self):
  for action in (lambda e:e['g'].materials['Timber']['color'].__setitem__(0,.5),lambda e:e['M'].__setitem__('new','Timber'),lambda e:setattr(e['g'],'group','Other')):
   with self.assertRaisesRegex(ValueError,'shared authoring state'):exec(self.hook,self.environment(action))
 def test_each_shared_rng_mutation_rejected(self):
  old_random=random.getstate();old_np=np.random.get_state()
  try:
   for action in (lambda e:e['rng'].uniform(),lambda e:random.random(),lambda e:np.random.uniform()):
    with self.assertRaisesRegex(ValueError,'shared random state'):exec(self.hook,self.environment(action))
  finally:random.setstate(old_random);np.random.set_state(old_np)
 def test_wrong_returned_shop_or_type_rejected(self):
  for value in ({'shop':'S02'},[],None):
   with self.assertRaisesRegex(ValueError,'wrong venue identity'):exec(self.hook,self.environment(lambda e:e.__setitem__('result',value)))
 def test_literal_feature_guard_rejects_false_and_malformed(self):
  guard=next(n for n in self.tree.body if isinstance(n,ast.If) and 'venue_projecting_signs' in ast.unparse(n.test));code=compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),str(SOURCE),'exec')
  for value in (False,None,0,1,1.0,'true',[],{}):
   with self.assertRaises(ValueError):exec(code,dict(FEATURES={'venue_projecting_signs':value,'s05_pendant_refinement':True}))
  exec(code,dict(FEATURES={'venue_projecting_signs':True,'s05_pendant_refinement':True}))
 def test_s05_provenance_version_remains_literal_218(self):
  node=next(n for n in self.tree.body if isinstance(n,ast.Assign) and "manifest['s05PendantRefinement']" in ast.unparse(n.targets[0]));kw={k.arg:k.value for k in node.value.keywords};self.assertEqual(ast.literal_eval(kw['version']),'2.18.0')
 def test_new_hook_follows_completed_shop_record(self):
  s=SOURCE.read_text();self.assertLess(s.index('shop_personality_records.append(build_shop('),s.index('sign_record=add_signs('));self.assertLess(s.index('sign_record=add_signs('),s.index('consume_legacy_shop_rng(rng)'))
if __name__=='__main__':unittest.main(verbosity=2)
