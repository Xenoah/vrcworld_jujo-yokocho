"""Frozen selected revision. Does not overwrite any historical pin or fixture."""
import copy,itertools,json,unittest
from pathlib import Path
import numpy as np
import mountain_detail_contract as detail
import mountain_quality_contract as quality
from mountain_detail_test_fixture import frozen_arrays
from mountain_quality_test_fixture import selected_arrays,restore_prior_mountains
from test_snow_deposition import geometry
from mountain_detail import apply_mountain_detail
from mountain_snow_craft import apply_mountain_snow_craft
from peer_culling_contract import summarize
ROOT=Path(__file__).resolve().parents[1]

class SelectedMountainQualityTests(unittest.TestCase):
 def test_source_gate_invalid_flags_are_atomic_and_off_is_legacy(self):
  from mountain_quality import apply_mountain_quality
  from test_snow_deposition import build,raw
  for enabled in (False,True):
   g=geometry();stats=apply_mountain_quality(g,dict(snow_deposition=enabled));self.assertEqual(stats,(None,None));g.compact();g.bake_mood([])
   old=build(enabled);self.assertEqual({k:raw(b) for k,b in g.batches.items()},{k:raw(b) for k,b in old.batches.items()})
  for features in [dict(mountain_detail='true'),dict(mountain_snow_craft=True),dict(mountain_seam_normals=True)]:
   g=geometry();before=copy.deepcopy(g.batches)
   with self.assertRaises(ValueError):apply_mountain_quality(g,features)
   self.assertEqual(before,g.batches)

 def test_selected_source_reproduces_frozen_arrays_exactly(self):
  g=geometry();apply_mountain_detail(g);apply_mountain_snow_craft(g,'soft');g.compact();g.bake_mood([])
  for b in selected_arrays():
   actual=g.batches[(b['group'],b['material'])]
   for old,new in [('vertices','v'),('uv','uv'),('faces','f')]:np.testing.assert_array_equal(b[old],actual[new])
   np.testing.assert_array_equal(b['colors'],(actual['colors']*255).astype('u1'))

 def test_selected_changes_only_eight_rgb_records(self):
  changed=[]
  for a,b in zip(frozen_arrays('after_snow'),selected_arrays()):
   for field in ('vertices','uv','faces'):np.testing.assert_array_equal(a[field],b[field])
   np.testing.assert_array_equal(a['colors'][:,3],b['colors'][:,3])
   if not np.array_equal(a['colors'],b['colors']):changed.append((b['group'],b['material']))
  self.assertEqual(changed,[k for k in detail.KEYS if k[1]!='AlpineRock'])

 def test_shared_snow_boundary_color_and_uv_continuity(self):
  bypos={};bases={'AlpineSnow':np.array((.88,.93,.97)),'AlpineSnowShade':np.array((.60,.72,.82))};rock=np.array((.025,.028,.0055));shared=0
  for b in selected_arrays():
   np.testing.assert_allclose(b['uv'],b['vertices'][:,:2]*.012,rtol=0,atol=4e-6)
   if b['material'] not in bases:continue
   ratio=rock/bases[b['material']];coverage=(b['colors'][:,:3]/255.-ratio)/(.95-ratio)
   for p,uv,c in zip(b['vertices'],b['uv'],coverage):bypos.setdefault(tuple(p),[]).append((uv,c))
  for values in bypos.values():
   if len(values)<2:continue
   shared+=1;self.assertLess(float(np.max(np.ptp([v[1] for v in values],axis=0))),.0048)
   for uv,_ in values[1:]:np.testing.assert_array_equal(uv,values[0][0])
  self.assertGreater(shared,100)

 def test_current_native_exact_selected_feature_contract(self):
  from peer_culling_contract import read_visual
  data=ROOT/'Assets/TreeTopYokocho/Data';path=data/'VisualMeshes.bytes'
  if not path.exists():self.skipTest('No current native export')
  manifest=json.loads((data/'WorldManifest.json').read_text());result=quality.validate_native_mountains(read_visual(path),manifest.get('features',{}));self.assertTrue(result['passed'],result)

 def test_literal_flags_and_dependency_matrix(self):
  names=('mountain_detail','snow_deposition','mountain_snow_craft','mountain_seam_normals')
  for values in itertools.product((False,True),repeat=4):
   f=dict(zip(names,values));adaptive,snow,craft,normals=values
   if (craft and not(adaptive and snow)) or (normals and not adaptive):
    with self.assertRaises(ValueError):quality.flags(f)
   else:
    self.assertEqual(quality.flags(f),values)
    expected=quality.expected_records(f);self.assertEqual(set(expected),set(detail.KEYS))
  for name in names:
   for value in ('true',1,0,None,[],{}):
    with self.assertRaises(ValueError):quality.flags({name:value})

 def test_exact_composition_old_snow_then_selected_and_unrelated_unchanged(self):
  for snow in (False,True):
   original={(r['group'],r['material']):dict(r,legacyMetadata='retained before substitution') for r in detail.load_oracle()['variants']['before_snow' if snow else 'before_plain']}
   sentinel=('Unrelated/Keep','Sentinel');original[sentinel]={'keep':[1,2,3]}
   for adaptive in (False,True):
    for craft in (False,True) if adaptive and snow else (False,):
     features=dict(mountain_detail=adaptive,snow_deposition=snow,mountain_snow_craft=craft,mountain_seam_normals=adaptive)
     result=quality.compose_expected_records(original,features)
     self.assertIs(result[sentinel],original[sentinel]);self.assertEqual(len(result),13)
     self.assertTrue(all('legacyMetadata' in original[k] for k in detail.KEYS))
     if adaptive:self.assertEqual({k:result[k] for k in detail.KEYS},quality.expected_records(features))
     else:self.assertEqual(result,original)
   bad=copy.deepcopy(original);bad[detail.KEYS[0]]['geometrySha256']='0'*64
   with self.assertRaises(ValueError):quality.compose_expected_records(bad,dict(mountain_detail=True,snow_deposition=snow))

 def test_strict_inverse_all_valid_variants_and_duplicate_rejection(self):
  for adaptive,snow,craft in [(False,False,False),(False,True,False),(True,False,False),(True,True,False),(True,True,True)]:
   batches=selected_arrays() if craft else frozen_arrays(('after' if adaptive else 'before')+('_snow' if snow else '_plain'))
   sentinel={'group':'Unrelated/Keep','material':'Sentinel','vertices':np.zeros((3,3),np.float32),'uv':np.zeros((3,2),np.float32),'colors':np.full((3,4),255,np.uint8),'faces':np.array([[0,1,2]],np.uint32)};batches.append(sentinel)
   features=dict(mountain_detail=adaptive,snow_deposition=snow,mountain_snow_craft=craft,mountain_seam_normals=adaptive,unrelated=True)
   manifest={'features':features,'mountainDetail':{'sentinel':1},'mountainSnowCraft':{'study':'soft'},'detail':{'landscapeTriangles':20000+3756*adaptive}}
   self.assertTrue(quality.validate_native_mountains(batches,features)['passed'])
   restored,m=restore_prior_mountains(batches,manifest);self.assertIs(restored[-1],sentinel)
   expected=frozen_arrays('before_snow' if snow else 'before_plain')
   self.assertEqual([summarize(b) for b in restored[:-1]],[summarize(b) for b in expected])
   if adaptive:
    self.assertEqual(m['features'],dict(snow_deposition=snow,unrelated=True));self.assertEqual(m['detail']['landscapeTriangles'],20000)
   self.assertEqual(manifest['features'],features)
   with self.assertRaises(ValueError):restore_prior_mountains(batches+[batches[0]],manifest)
   bad=copy.deepcopy(batches);bad[0]['colors'][0,0]^=1
   with self.assertRaises(ValueError):restore_prior_mountains(bad,manifest)

 def test_no_test_fixture_in_production_and_frozen_v1_still_exact(self):
  detail.load_oracle();quality.load_oracle()
  for name in ('mountain_quality.py','mountain_detail.py','mountain_detail_contract.py','mountain_quality_contract.py','mountain_snow_craft.py','mountain_seam_normals.py'):
   text=(ROOT/'Source'/name).read_text();self.assertNotIn('test_fixture import',text);self.assertNotIn('restore_prior',text)

if __name__=='__main__':unittest.main(verbosity=2)
