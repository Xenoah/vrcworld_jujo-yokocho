"""Portable, read-only snow-deposition source/native regression.

Run with the project's Python: python Source/test_snow_deposition.py
Uses only the production module and the existing immutable v2.8 peer baseline.
No staging directory, old source archive, full build, Blender, or Unity required.
When a native export exists, its literal manifest feature selects before/after.
"""
from pathlib import Path
import ast
import argparse
import copy
import hashlib
import json
import random
import struct
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import numpy as np
import fantasy_landscape as landscape
from world_geometry import Geometry

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT/'Docs/baselines/verified_peer_culling_2.8.0.json'
BASELINE_SHA256 = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
AFTER = {
 ('Landscape/SnowRange_0', 'AlpineSnow'): '78d932fa17182d8796aa176ca091924ab7425c8b707311a4983998abdc1d06db',
 ('Landscape/SnowRange_0', 'AlpineSnowShade'): '54dc6ef6dde6cfe62add9021d3667f333daeffa4b3a7e01707244ec92f64fde7',
 ('Landscape/SnowRange_1', 'AlpineSnow'): '955a599ebc5f64999266b94d0d239b36c889a1ea610e14ff12aded27fe41c821',
 ('Landscape/SnowRange_1', 'AlpineSnowShade'): 'a31d8b056968ea5a132c6d0f27004f8dd92ceefb42af167cd5439698cd7c2825',
 ('Landscape/SnowRange_2', 'AlpineSnow'): '83f41635fc969571b67f33e6e07f3cff4177aeefaa6669bf56b888bac821fa6a',
 ('Landscape/SnowRange_2', 'AlpineSnowShade'): 'cd409e7e28b21de58166ecb2f900c83d5a98790567b1a5554d5b33cabe929662',
 ('Landscape/SnowRange_3', 'AlpineSnow'): '7d61d1bd83d2ba474d884e84f4f07eddbfb05fd7427b6bea1ad042a268ba4460',
 ('Landscape/SnowRange_3', 'AlpineSnowShade'): '255678dcf69988b03a7bb0fc210005a330c4611b28c105f2948c98a43e5f4f69',
}
ORIGINAL_AST = {
 '_mountain_height': '94856d7d33f17a4cc758545c0dd26a644e29a9a62df514f5c52556f3cda35fb3',
 '_clip_snow': 'a29db96ab76d6b8c5e2bec36847c818f2e8e54b59f6e38b0464f147110e69b26',
 '_mountains': '14ff981161b95b53a5b2afdf5b9a265d04a625113a00652fcf180319af664501',
}


def sha(data):
 return hashlib.sha256(data).hexdigest()


def fields(batch):
 return {name: np.asarray(batch[name], dtype=dtype).tobytes()
         for name, dtype in [('v','<f4'), ('uv','<f4'), ('f','<u4')]} | {
             'colors': (np.asarray(batch['colors'])*255).astype('u1').tobytes()}


def raw(batch):
 data=fields(batch)
 return b''.join(data[name] for name in ('v','uv','colors','f'))


def geometry():
 g=Geometry()
 g.material('AlpineRock',(.31,.36,.40),'PBR/rocky_terrain_02_diff_4k.jpg',roughness=1)
 g.material('AlpineSnow',(.88,.93,.97),roughness=.92)
 g.material('AlpineSnowShade',(.60,.72,.82),roughness=.95)
 landscape._mountains(g,'AlpineRock','AlpineSnow','AlpineSnowShade')
 return g


def build(enabled):
 g=geometry()
 if enabled is True: landscape.apply_snow_deposition(g)
 g.compact();g.bake_mood([])
 return g


def native_mountains(path):
 """Read only the twelve relevant records, skipping unrelated payload bytes."""
 result={}
 with path.open('rb') as stream:
  if stream.read(4)!=b'JYWM':raise ValueError('Invalid native header')
  version,count=struct.unpack('<II',stream.read(8))
  if version!=1:raise ValueError('Unsupported native version')
  for _ in range(count):
   names=[]
   for __ in range(2):
    size=struct.unpack('<I',stream.read(4))[0]
    names.append(stream.read(size).decode())
   nv,ni=struct.unpack('<II',stream.read(8));size=nv*24+ni*4;key=tuple(names)
   if names[0].startswith('Landscape/SnowRange_'):
    if key in result:raise ValueError('Duplicate mountain batch')
    data=stream.read(size)
    if len(data)!=size:raise ValueError('Truncated mountain payload')
    result[key]=data
   else:stream.seek(size,1)
  if stream.read(1):raise ValueError('Trailing native data')
 return result


class SnowDepositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  content=BASELINE.read_bytes()
  if sha(content)!=BASELINE_SHA256:raise AssertionError('Original v2.8 baseline changed')
  records=json.loads(content)['protectedGroups']
  selected=[r for r in records if r['group'].startswith('Landscape/SnowRange_')]
  cls.pinned={(r['group'],r['material']):r for r in selected}
  if len(selected)!=12 or len(cls.pinned)!=12:raise AssertionError('Expected exactly twelve original mountain records')
  cls.before=build(False);cls.after=build(True)

 def test_original_isolated_records_match_immutable_baseline(self):
  self.assertEqual(set(self.before.batches),set(self.pinned))
  for key,b in self.before.batches.items():
   record=self.pinned[key];f=fields(b)
   self.assertEqual(len(b['v']),record['vertices'],key)
   self.assertEqual(len(b['f']),record['triangles'],key)
   self.assertEqual(sha(f['v']+f['f']),record['geometrySha256'],key)
   self.assertEqual(sha(raw(b)),record['attributesAndIndicesSha256'],key)

 def test_exact_eight_approved_colors_and_immutable_fields(self):
  self.assertEqual(self.before.materials,self.after.materials)
  self.assertEqual(list(self.before.batches),list(self.after.batches))
  changed=set()
  for key,b in self.before.batches.items():
   new=self.after.batches[key];old_fields,new_fields=fields(b),fields(new)
   for field in ('v','uv','f'):self.assertEqual(old_fields[field],new_fields[field],(key,field))
   self.assertTrue(np.array_equal(b['colors'][:,3],new['colors'][:,3]),key)
   self.assertTrue(np.isfinite(new['colors']).all(),key)
   self.assertTrue(((new['colors']>=0)&(new['colors']<=1)).all(),key)
   if old_fields['colors']!=new_fields['colors']:changed.add(key)
   expected=AFTER.get(key,self.pinned[key]['attributesAndIndicesSha256'])
   self.assertEqual(sha(raw(new)),expected,key)
  self.assertEqual(changed,set(AFTER))
  self.assertEqual(sum(len(b['v']) for b in self.after.batches.values()),7461)
  self.assertEqual(sum(len(b['f']) for b in self.after.batches.values()),11500)

 def test_original_generation_functions_ast_is_unchanged(self):
  tree=ast.parse(Path(landscape.__file__).read_text())
  functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
  for name,expected in ORIGINAL_AST.items():
   self.assertEqual(sha(ast.dump(functions[name],include_attributes=False).encode()),expected,name)

 def test_rng_and_unrelated_batch_are_unchanged(self):
  g=geometry();g.group='Unrelated/Sentinel';g.material('Unrelated',(1,1,1))
  g.add([(1,2,3),(4,5,6),(7,8,10)],[(0,1,2)],'Unrelated',[(1,1),(2,2),(3,3)])
  sentinel=copy.deepcopy(g.batches[('Unrelated/Sentinel','Unrelated')]);materials=copy.deepcopy(g.materials)
  py=random.getstate();nr=np.random.get_state();landscape.apply_snow_deposition(g)
  self.assertEqual(sentinel,g.batches[('Unrelated/Sentinel','Unrelated')]);self.assertEqual(materials,g.materials)
  self.assertEqual(py,random.getstate());after=np.random.get_state()
  self.assertEqual(nr[0],after[0]);np.testing.assert_array_equal(nr[1],after[1]);self.assertEqual(nr[2:],after[2:])

 def test_every_dark_sublevel_component_reaches_original_rock(self):
  original=landscape._connected_snow_coverage;capture={}
  def record(points,faces,boundary):
   cover=original(points,faces,boundary);capture.update(points=points,faces=faces,boundary=boundary,cover=cover);return cover
  g=geometry()
  with patch.object(landscape,'_connected_snow_coverage',record):landscape.apply_snow_deposition(g)
  points,faces,boundary,cover=(capture[x] for x in ('points','faces','boundary','cover'))
  self.assertEqual(len(points),2845);self.assertEqual(len(boundary),654);self.assertTrue(np.all(cover[boundary]==0))
  initial=landscape._mountain_snow_coverage(points);initial[boundary]=0
  self.assertTrue(np.all(cover>=initial));self.assertTrue(np.any(cover>initial+1e-10))
  neighbors=[set() for _ in points]
  for a,b,c in faces:neighbors[a].update((b,c));neighbors[b].update((a,c));neighbors[c].update((a,b))
  parent=list(range(len(points)));active=set();seed=set(boundary);root_seed={i:i in seed for i in parent}
  def find(i):
   while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
   return i
  levels=np.unique(cover);self.assertGreater(len(levels),100)
  for value in levels:
   ids=list(map(int,np.where(cover==value)[0]));active.update(ids)
   for i in ids:
    for j in neighbors[i]&active:
     a,b=find(i),find(j)
     if a!=b:parent[b]=a;root_seed[a]=root_seed[a] or root_seed[b]
   for i in active:self.assertTrue(root_seed[find(i)],('detached exposure',float(value),i))

 def test_disabled_pass_and_repeated_enabled_build_are_exact(self):
  for enabled,reference in [(False,self.before),(True,self.after)]:
   again=build(enabled)
   for key,b in reference.batches.items():self.assertEqual(raw(b),raw(again.batches[key]),(enabled,key))

 def test_current_native_respects_literal_manifest_feature(self):
  data=ROOT/'Assets/TreeTopYokocho/Data';path=data/'VisualMeshes.bytes'
  if not path.exists():self.skipTest('No current native export; isolated generation checks still run')
  manifest=json.loads((data/'WorldManifest.json').read_text());features=manifest.get('features',{})
  self.assertIsInstance(features,dict)
  flag=features.get('snow_deposition',False)
  self.assertIs(type(flag),bool,'snow_deposition must be a literal JSON Boolean when present')
  from mountain_quality_contract import flags as quality_flags,validate_native_mountains
  quality_flags(features) # Literal types and feature dependencies fail closed.
  if features.get('mountain_detail') is True:
   from peer_culling_contract import read_visual
   result=validate_native_mountains(read_visual(path),features);self.assertTrue(result['passed'],result);return
  expected=self.after if flag is True else self.before
  actual=native_mountains(path);self.assertEqual(set(actual),set(expected.batches))
  for key,b in expected.batches.items():self.assertEqual(actual[key],raw(b),(flag,key))


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
 if args.report:
  args.report.write_text(json.dumps({'scope':'Portable source and exact native snow contracts; not Unity or runtime verification','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'productionSourceSha256':hashlib.sha256((ROOT/'Source/fantasy_landscape.py').read_bytes()).hexdigest()},indent=2)+'\n')
 sys.exit(not result.wasSuccessful())
