"""Portable material-only regression; no Blender, Unity or full generation."""
from pathlib import Path
import argparse,ast,copy,json,random,sys,unittest
import numpy as np
from world_geometry import Geometry
from stage_wood_finish import apply_stage_wood_finish,OLD_FILES,NEW_FILES,FIELDS,MATERIAL
ROOT=Path(__file__).resolve().parent.parent

def fixture():
 g=Geometry();g.materials={MATERIAL:dict(name=MATERIAL,color=[.98,.87,.66],roughness=.82,uvScale=.75,normalScale=1,parallax=.014,**OLD_FILES),'Cedar':dict(name='Cedar',color=[.94,.76,.57],**NEW_FILES),'Untouched':dict(name='Untouched',arm='other.png')}
 g.group='Stage/Noh/Floor';g.box([0,0,0],[1,1,1],MATERIAL)
 return g

class StageFinishContracts(unittest.TestCase):
 def test_exact_four_fields_and_no_geometry_or_other_material_change(self):
  g=fixture();before=copy.deepcopy(g.__dict__);out=apply_stage_wood_finish(g)
  changed=[k for k in before['materials'][MATERIAL] if before['materials'][MATERIAL][k]!=g.materials[MATERIAL][k]]
  self.assertEqual(set(changed),set(FIELDS));self.assertEqual(out['newTextureFiles'],0)
  expected=copy.deepcopy(before);expected['materials'][MATERIAL].update(NEW_FILES)
  self.assertEqual(expected,g.__dict__)
 def test_shared_texture_set_exists_and_remains_coherent(self):
  for field,path in NEW_FILES.items():self.assertTrue((ROOT/'Assets/TreeTopYokocho/Textures'/path).is_file(),field)
  self.assertTrue(all('wood_planks_grey_' in x for x in NEW_FILES.values()))
 def test_repeat_and_drift_fail_atomically(self):
  for mode in ('repeat','old','reference'):
   g=fixture()
   if mode=='repeat':apply_stage_wood_finish(g)
   elif mode=='old':g.materials[MATERIAL]['arm']='custom.png'
   else:g.materials['Cedar']['normal']='custom.png'
   before=copy.deepcopy(g.__dict__)
   with self.assertRaises(ValueError):apply_stage_wood_finish(g)
   self.assertEqual(before,g.__dict__)
 def test_global_rng_unchanged(self):
  g=fixture();py=random.getstate();nr=np.random.get_state();apply_stage_wood_finish(g)
  self.assertEqual(py,random.getstate());after=np.random.get_state()
  self.assertEqual(nr[0],after[0]);np.testing.assert_array_equal(nr[1],after[1]);self.assertEqual(nr[2:],after[2:])
 def test_literal_builder_gate(self):
  tree=ast.parse((ROOT/'Source/build_world.py').read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='apply_stage_wood_finish']
  self.assertEqual(len(calls),1)
  assignments=[n for n in ast.walk(tree) if isinstance(n,ast.IfExp) and calls[0] in list(ast.walk(n.body))]
  self.assertEqual(len(assignments),1)
  expected=ast.parse("stage and FEATURES.get('stage_roof_craft') is True",mode='eval').body
  self.assertEqual(ast.dump(assignments[0].test,include_attributes=False),ast.dump(expected,include_attributes=False))
 def test_current_manifest_only_when_enabled(self):
  p=ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json'
  if not p.exists():self.skipTest('No current exported manifest')
  m=json.loads(p.read_text());spec=next(x for x in m['materials'] if x['name']==MATERIAL)
  expected=NEW_FILES if m.get('features',{}).get('stage_roof_craft') is True else OLD_FILES
  self.assertEqual({k:spec[k] for k in FIELDS},expected)
  self.assertEqual(spec['roughness'],.82);self.assertEqual(spec['uvScale'],.75)
  self.assertEqual(spec['color'],[.98,.87,.66])

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path);args=p.parse_args()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StageFinishContracts))
 if args.report:args.report.write_text(json.dumps({'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'scope':'Exact source/material mapping; not shader compilation or runtime'},indent=2)+'\n')
 sys.exit(not result.wasSuccessful())
