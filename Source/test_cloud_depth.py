"""Portable cloud-depth source/native tests, without copied generators or binaries.

Imports production cloud_sea, world_geometry and cloud_depth. The original eight
native summaries come from the existing immutable v2.8 peer baseline. A 5.7 KB
pinned JSON supplies only exact RNG/metadata context. No world build or renderer
is executed. --report writes the completed unittest result when requested.
"""
from pathlib import Path
import argparse,ast,copy,hashlib,json,pickle,random,re,struct,sys,tempfile,unittest
import numpy as np
sys.dont_write_bytecode=True
import cloud_sea as legacy
import world_geometry as geometry
import cloud_depth as depth

ROOT=Path(__file__).resolve().parents[1]
BASELINE=ROOT/'Docs/baselines/verified_peer_culling_2.8.0.json'
CONTEXT=ROOT/'Docs/baselines/verified_cloud_source_context_2.11.0.json'
BASELINE_SHA='32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
CONTEXT_SHA='dc9a72e20848197dbe6b0d9405eb1afe8bc174cd4edc0cb0e34ccc4f447741f8'
GENERATOR_SHA='f200cfa3925eb4662b7945849b3e417e34b8b15a5fec097387bfd58fb8a422bc'
SHADER_SHA='44293158c2b86e5c270d9f77a3d3e3ef5e6f74275fcb9afe5b14465ec411e097'
ORIGINAL_NATIVE_SHA='30c9fe9954fd4a32d76c5244476be893d76b9b9260097dc6a39e43ca67598425'
AFTER_NATIVE_SHA='0755cb8c239bab3a96c09ae6724414dba35e2d4eebd9034618c3179421503612'
# Independent approved float64-source-pipeline after hashes, not production gates.
AFTER={
 ('Landscape/CloudSea_Near_NW','CloudSeaSilver'):('97006ec2205d260f92d1426386f3732e17799d63fb28883fb518ba25fea5cd30','192c639efd14684157a634527fc2029d190dc76b479b87da17e9c94cfdd0cb2c'),
 ('Landscape/CloudSea_Near_NE','CloudSeaSilver'):('1187b789653e92bcc423626d95b34f02ce32c36197ee8ffe4755e944012c7bba','0d2bed6a4cbcfd6dbf0c512724650234506d54bc6971cd3e3921599e4cac2f6d'),
 ('Landscape/CloudSea_Near_SW','CloudSeaSilver'):('c410e6dcab05841783685dca8d545a84cbff90aade9cb43d27ad287b8df23a09','3f65d7b9cddc906f2f762cdb9775599d44944ea7c1bf339cf6a3fbbdda7366b5'),
 ('Landscape/CloudSea_Near_SE','CloudSeaSilver'):('9997de3a3814b86b2b24aac6ae1c46b6a9df3d84cf3e727c388b2cc28cd11379','30df1cf7353beb68886f0acb563a3ae819146bad2f231c466e3c3ac4edc7c2bc'),
 ('Landscape/CloudSea_Far_NW','CloudSeaSilver'):('40da297159ab0045dc60c5cf0229a23ff325132679fbfec5fcdbb7f6eb1d8a9f','1ca464e0853e9f1c7e259822380ba00e63ce808841293428cee47521ea4ab62b'),
 ('Landscape/CloudSea_Far_NE','CloudSeaSilver'):('99eeb4951945d559111b05b7334629fffc7d755bca27c9ec4043b5e07bb58267','9a2595032e5a1d6f0d58d29d2a1510ebeb48b7d51c04cd206b3d2f387337411c'),
 ('Landscape/CloudSea_Far_SW','CloudSeaSilver'):('9c2656172ea19f809e6877c19817269f2a98ca8d73fbebce636eae1faed55743','01271b20d6ed0d3c520441e248e07d1c17b40346f32febec4cb5cc31f67a9798'),
 ('Landscape/CloudSea_Far_SE','CloudSeaSilver'):('4a5d45d82158d00cffd21a97ed276d1f1c7ecba6886aa1ea9af51fa509a79961','99d15f1aa5540b08a8f692a9fc0836f0c13e1479382f1e929abbd82d51818ba2'),
}
KEYS=tuple(AFTER)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def key(row):return row['group'],row['material']
def pinned(path,digest):
 raw=path.read_bytes()
 if sha(raw)!=digest:raise ValueError('Pinned fixture file changed: '+path.name)
 return json.loads(raw)
def before_summaries():
 rows=pinned(BASELINE,BASELINE_SHA)['protectedGroups']
 result={key(row):{f:row[f] for f in ('group','material','vertices','triangles','geometrySha256','attributesAndIndicesSha256')} for row in rows if key(row) in AFTER}
 if set(result)!=set(AFTER):raise ValueError('Missing pinned original cloud record')
 return result

def actual_source():
 context=pinned(CONTEXT,CONTEXT_SHA)
 rng=np.random.default_rng();rng.bit_generator.state=context['bitGeneratorState']
 g=geometry.Geometry();md=legacy.add_cloud_sea(g,{},rng)
 return g,md,rng

def native_rows(g):
 return [dict(group=k[0],material=k[1],vertices=np.asarray(b['v'],'<f4'),uv=np.asarray(b['uv'],'<f4'),colors=(np.asarray(b.get('colors',np.ones((len(b['v']),4))))*255).astype('u1'),faces=np.asarray(b['f'],'<u4')) for k,b in g.batches.items()]
def raw_attributes(b):return b''.join(np.asarray(b[f],d).tobytes() for f,d in [('vertices','<f4'),('uv','<f4'),('colors','u1'),('faces','<u4')])
def summarize(b):
 v=np.asarray(b['vertices'],'<f4').tobytes();f=np.asarray(b['faces'],'<u4').tobytes()
 return dict(group=b['group'],material=b['material'],vertices=len(b['vertices']),triangles=len(b['faces']),geometrySha256=sha(v+f),attributesAndIndicesSha256=sha(raw_attributes(b)))
def build(enabled):
 g,md,_=actual_source()
 if enabled is True:depth.apply_cloud_depth(g,md)
 g.compact();g.bake_mood([])
 return g,md

def read_native_clouds(path):
 """Stream only cloud fields; unrelated native data is never loaded into memory."""
 result=[];size=path.stat().st_size
 with path.open('rb') as stream:
  def exact(n):
   if n<0 or stream.tell()+n>size:raise ValueError('Invalid native field length')
   raw=stream.read(n)
   if len(raw)!=n:raise ValueError('Truncated native field')
   return raw
  if exact(4)!=b'JYWM':raise ValueError('Invalid native signature')
  version,count=struct.unpack('<II',exact(8))
  if version!=1:raise ValueError('Unsupported native version')
  for _ in range(count):
   group,material=[exact(struct.unpack('<I',exact(4))[0]).decode() for __ in range(2)]
   nv,ni=struct.unpack('<II',exact(8));length=nv*24+ni*4
   if ni%3:raise ValueError('Nontriangular native indices')
   if group.startswith('Landscape/CloudSea'):
    if (group,material) not in AFTER:raise ValueError('Unapproved cloud identity')
    if (group,material) in {key(b) for b in result}:raise ValueError('Duplicate cloud identity')
    result.append(dict(group=group,material=material,vertices=np.frombuffer(exact(nv*12),'<f4').reshape(-1,3),uv=np.frombuffer(exact(nv*8),'<f4').reshape(-1,2),colors=np.frombuffer(exact(nv*4),'u1').reshape(-1,4),faces=np.frombuffer(exact(ni*4),'<u4').reshape(-1,3)))
   else:
    if stream.tell()+length>size:raise ValueError('Truncated unrelated native payload')
    stream.seek(length,1)
  if stream.read(1):raise ValueError('Trailing native data')
 if {key(b) for b in result}!=set(AFTER):raise ValueError('Missing cloud identities')
 return result

def matches_native(rows,manifest):
 features=manifest.get('features',{})
 enabled=isinstance(features,dict) and features.get('cloud_depth') is True
 wanted=before_summaries()
 if enabled:
  for k,(geometry_hash,payload_hash) in AFTER.items():
   wanted[k]=dict(wanted[k],geometrySha256=geometry_hash,attributesAndIndicesSha256=payload_hash)
 actual=[summarize(row) for row in rows]
 return len(actual)==8 and len({key(r) for r in actual})==8 and {key(r):r for r in actual}==wanted

def json_differences(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  result=[]
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:result.append(path+'/'+k)
   else:result.extend(json_differences(a[k],b[k],path+'/'+k))
  return result
 if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):return [p for i,(x,y) in enumerate(zip(a,b)) for p in json_differences(x,y,path+'/'+str(i))]
 return [] if a==b else [path]

def segment_hits(triangles,start,end):
 """Double-sided, finite-segment Moller-Trumbore geometry probe."""
 start=np.asarray(start,float);direction=np.asarray(end,float)-start
 e1=triangles[:,1]-triangles[:,0];e2=triangles[:,2]-triangles[:,0]
 h=np.cross(np.broadcast_to(direction,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h)
 mask=abs(a)>1e-10;inv=np.zeros_like(a);inv[mask]=1/a[mask]
 s=start-triangles[:,0];u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1)
 v=inv*(q@direction);t=inv*np.einsum('ij,ij->i',e2,q)
 return np.flatnonzero(mask&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>=0)&(t<=1))

def altitude_block():
 """Compile the real production cloud checks, bounded by cloud/peer bindings."""
 path=ROOT/'Source/validate_altitude.py';tree=ast.parse(path.read_text(),filename=str(path))
 def assigns(node,name):return isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)
 starts=[i for i,n in enumerate(tree.body) if assigns(n,'cloud')];ends=[i for i,n in enumerate(tree.body) if assigns(n,'peer')]
 if len(starts)!=1 or len(ends)!=1 or not starts[0]<ends[0]:raise ValueError('Ambiguous production altitude cloud block')
 block=tree.body[starts[0]+1:ends[0]];names={n.id for node in block for n in ast.walk(node) if isinstance(n,ast.Name)}
 if not {'cloud_depth','cloud_lower'}<=names:raise ValueError('Production altitude validator lacks the literal cloud-depth block')
 module=ast.Module(body=block,type_ignores=[]);ast.fix_missing_locations(module)
 return compile(module,str(path),'exec')


class CloudDepthTests(unittest.TestCase):
 def setUp(self):
  self.g,self.md,self.rng=actual_source()

 def test_existing_baseline_context_and_production_source_are_pinned(self):
  before=before_summaries();context=pinned(CONTEXT,CONTEXT_SHA)
  self.assertEqual(set(before),set(KEYS));self.assertEqual(len(before),8)
  self.assertEqual(sha(Path(legacy.__file__).read_bytes()),GENERATOR_SHA)
  self.assertEqual(self.md,context['legacyCloudMetadata'])
  rng=np.random.default_rng(context['worldSeed']);rng.bit_generator.advance(context['rawStepsToCloud'])
  self.assertEqual(rng.bit_generator.state['state'],context['bitGeneratorState']['state'])
  self.assertEqual(tuple(depth.CLOUD_KEYS),KEYS)
  for module in (legacy,geometry,depth):
   self.assertEqual(Path(module.__file__).resolve().parent,(ROOT/'Source').resolve(),'Production module imported outside this repo layout')

 def test_omission_reproduces_actual_native_baseline_exactly(self):
  self.assertEqual(self.md,pinned(CONTEXT,CONTEXT_SHA)['legacyCloudMetadata'])
  self.g.compact();self.g.bake_mood([])
  with tempfile.TemporaryDirectory(prefix='cloud-depth-test-') as directory:
   p=Path(directory)/'legacy.bytes';self.g.save_binary(p)
   self.assertEqual(sha(p.read_bytes()),ORIGINAL_NATIVE_SHA)
   self.assertEqual({key(row):summarize(row) for row in native_rows(self.g)},before_summaries())

 def test_exact_only_z_source_and_export_transform(self):
  before=copy.deepcopy(self.g.batches)
  depth.apply_cloud_depth(self.g,self.md)
  for key,b in self.g.batches.items():
   old=np.asarray(before[key]['v']);new=np.asarray(b['v'])
   self.assertEqual(old[:,:2].tobytes(),new[:,:2].tobytes())
   self.assertEqual((124.-(124.-old[:,2])*2.2).tobytes(),new[:,2].tobytes())
   for attribute in ['f','uv']:self.assertEqual(before[key][attribute],b[attribute])
  self.g.compact();self.g.bake_mood([])
  oldg,_=build(False);oldrows=native_rows(oldg)
  for old,new in zip(oldrows,native_rows(self.g)):
   self.assertEqual(old['vertices'][:,:2].tobytes(),new['vertices'][:,:2].tobytes())
   for attr in ['uv','colors','faces']:self.assertEqual(old[attr].tobytes(),new[attr].tobytes())
   expected=np.asarray(124.-(124.-np.asarray(before[(old['group'],old['material'])]['v'])[:,2])*2.2,dtype='<f4')
   self.assertEqual(expected.tobytes(),new['vertices'][:,2].tobytes())

 def test_field_allowlist_and_all_rng_states(self):
  g=self.g;g.group='Unrelated/OwnerGroup'
  g.batches[('Tree/DoNotChange','Bark')]={'v':[[1.,2.,119.],[3.,4.,120.],[5.,6.,121.]],'uv':[[0,0],[1,0],[1,1]],'f':[[0,1,2]],'colors':[[.1,.2,.3,1]]*3,'authored_tints':[(0,3,[.7,.8,.9])]}
  g.materials['Bark']={'name':'Bark','texture':'bark.png','color':[.6,.7,.8],'cloudBaseZ':110.}
  noncloud=copy.deepcopy(g.batches[('Tree/DoNotChange','Bark')]);identity=id(g.batches[('Tree/DoNotChange','Bark')])
  materials=copy.deepcopy(g.materials);old=copy.deepcopy(self.md)
  py=random.getstate();np_global=pickle.dumps(np.random.get_state());rng=copy.deepcopy(self.rng.bit_generator.state)
  refs={k:{a:id(v) for a,v in b.items() if a!='v'} for k,b in g.batches.items()}
  result=depth.apply_cloud_depth(g,self.md)
  self.assertIs(result,self.md);self.assertEqual(g.group,'Unrelated/OwnerGroup')
  self.assertEqual(noncloud,g.batches[('Tree/DoNotChange','Bark')]);self.assertEqual(identity,id(g.batches[('Tree/DoNotChange','Bark')]))
  self.assertEqual(py,random.getstate());self.assertEqual(np_global,pickle.dumps(np.random.get_state()));self.assertEqual(rng,self.rng.bit_generator.state)
  self.assertEqual(json_differences(materials,g.materials),['/CloudSeaSilver/cloudBaseZ'])
  self.assertEqual(set(json_differences(old,self.md)),{'/altitudeBounds/0','/altitudeBounds/1','/depthRefinement'}|{'/banks/%d/center/2'%i for i in range(28)})
  self.assertEqual(refs,{k:{a:id(v) for a,v in b.items() if a!='v'} for k,b in g.batches.items()})

 def test_cost_envelope_and_north_south_clear_views(self):
  depth.apply_cloud_depth(self.g,self.md);self.g.compact();self.g.bake_mood([])
  rows=native_rows(self.g);vertices=np.concatenate([b['vertices'] for b in rows]);tri=np.concatenate([b['vertices'][b['faces']] for b in rows])
  self.assertEqual(len(rows),8);self.assertEqual(len(vertices),20412);self.assertEqual(len(tri),36288)
  self.assertGreaterEqual(vertices[:,2].min(),93.2);self.assertLess(vertices[:,2].max()+.15,124.)
  self.assertGreaterEqual(134.-(vertices[:,2].max()+.15),10.)
  for gap in self.md['viewingBreaks'][:2]:self.assertEqual(len(segment_hits(tri,*gap['clearRayExample'])),0)
  with tempfile.TemporaryDirectory(prefix='cloud-depth-test-') as directory:
   p=Path(directory)/'deep.bytes';self.g.save_binary(p)
   self.assertEqual(p.stat().st_size,925800)
   self.assertEqual(sha(p.read_bytes()),AFTER_NATIVE_SHA)
  for row in rows:
   wanted=before_summaries()[key(row)]
   self.assertEqual((len(row['vertices']),len(row['faces'])),(wanted['vertices'],wanted['triangles']))
   self.assertEqual((summarize(row)['geometrySha256'],summarize(row)['attributesAndIndicesSha256']),AFTER[key(row)])

 def test_shader_source_is_exact_and_one_pass(self):
  raw=(ROOT/'Assets/TreeTopYokocho/Shaders/YokochoCloudSea.shader').read_bytes()
  self.assertEqual(sha(raw),SHADER_SHA);source=raw.decode()
  builder=(ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
  self.assertNotIn('cloudBaseZ',builder);self.assertNotIn('cloudTopZ',builder)
  self.assertEqual(len(re.findall(r'^\s*Pass\s*$',source,re.M)),1)
  self.assertIn('_Swell("Vertical drift metres", Range(0,.15)) = .12',source)
  self.assertNotIn('cloudBaseZ',source);self.assertNotIn('cloudTopZ',source)
  self.assertNotIn('tex2D',source);self.assertNotIn('GrabPass\n',source)

 def test_repeat_rejected_without_additional_mutation(self):
  depth.apply_cloud_depth(self.g,self.md);before=pickle.dumps((self.g.__dict__,self.md))
  with self.assertRaises(ValueError):depth.apply_cloud_depth(self.g,self.md)
  self.assertEqual(pickle.dumps((self.g.__dict__,self.md)),before)

 def test_bad_inputs_fail_atomically(self):
  mutators=[lambda g,m:g.compact(),lambda g,m:g.batches.pop(depth.CLOUD_KEYS[-1]),
   lambda g,m:g.batches.__setitem__(('Landscape/CloudSea_Near_NW_Alias',depth.MATERIAL_NAME),copy.deepcopy(g.batches[depth.CLOUD_KEYS[0]])),
   lambda g,m:m.__setitem__('triangles',1),lambda g,m:m['altitudeBounds'].__setitem__(0,0),
   lambda g,m:g.batches[depth.CLOUD_KEYS[0]]['v'][0].__setitem__(2,125),
   lambda g,m:g.materials[depth.MATERIAL_NAME].__setitem__('cloudBaseZ',90),
   lambda g,m:m['banks'][3].__setitem__('id','CloudBankNotReal'),
   lambda g,m:m['banks'][3].__setitem__('center',tuple(m['banks'][3]['center']))]
  for mutate in mutators:
   g,m,_=actual_source();mutate(g,m);before=pickle.dumps((g.__dict__,m))
   with self.assertRaises(ValueError):depth.apply_cloud_depth(g,m)
   self.assertEqual(pickle.dumps((g.__dict__,m)),before)

 def test_twelve_seeds_preserve_rng_cost_and_views(self):
  for seed in range(12):
   g=geometry.Geometry();rng=np.random.default_rng(seed);md=legacy.add_cloud_sea(g,{},rng);state=copy.deepcopy(rng.bit_generator.state)
   depth.apply_cloud_depth(g,md);self.assertEqual(state,rng.bit_generator.state)
   g.compact();rows=native_rows(g);tri=np.concatenate([b['vertices'][b['faces']] for b in rows])
   self.assertEqual(len(rows),8);self.assertEqual(len(tri),36288);self.assertLess(float(tri[:,:,2].max())+.15,124.)
   for gap in md['viewingBreaks'][:2]:self.assertEqual(len(segment_hits(tri,*gap['clearRayExample'])),0)


 def test_current_native_uses_only_literal_manifest_flag(self):
  data=ROOT/'Assets/TreeTopYokocho/Data';visual=data/'VisualMeshes.bytes';manifest=data/'WorldManifest.json'
  if not visual.exists() and not manifest.exists():self.skipTest('No native export supplied; source-only test root')
  self.assertTrue(visual.exists() and manifest.exists(),'Native geometry/manifest must be present together')
  md=json.loads(manifest.read_text());rows=read_native_clouds(visual)
  self.assertTrue(matches_native(rows,md),'Actual cloud fields differ from literal feature-selected exact payloads')
  features=md.get('features',{});enabled=isinstance(features,dict) and features.get('cloud_depth') is True
  expected_geometry,expected_metadata=build(enabled)
  self.assertEqual(md['cloudSea'],expected_metadata,'Actual cloud metadata differs from the exact selected source profile')
  observed=[m for m in md['materials'] if m['name']=='CloudSeaSilver']
  self.assertEqual(observed,[expected_geometry.materials['CloudSeaSilver']])

 def test_synthetic_literal_states_and_wrong_payloads(self):
  old,_=build(False);new,_=build(True);before,after=native_rows(old),native_rows(new)
  for flag in (None,False,0,1,1.0,'true','True','false',{},[],np.bool_(True)):
   m={'features':{'cloud_depth':flag}}
   self.assertTrue(matches_native(before,m),repr(flag));self.assertFalse(matches_native(after,m),repr(flag))
  self.assertTrue(matches_native(before,{}));self.assertFalse(matches_native(after,{}))
  self.assertTrue(matches_native(after,{'features':{'cloud_depth':True}}))
  self.assertFalse(matches_native(before,{'features':{'cloud_depth':True}}))
  for index,row in enumerate(after):
   for field,column in [('vertices',0),('vertices',1),('vertices',2),('uv',0),('colors',0),('colors',3)]:
    changed=dict(row);changed[field]=row[field].copy()
    if field=='colors':changed[field][0,column]^=1
    else:changed[field][0,column]=np.nextafter(changed[field][0,column],np.float32(np.inf))
    self.assertFalse(matches_native(after[:index]+[changed]+after[index+1:],{'features':{'cloud_depth':True}}),(key(row),field,column))
   changed=dict(row);changed['faces']=row['faces'].copy();changed['faces'][0]=changed['faces'][0,[0,2,1]]
   self.assertFalse(matches_native(after[:index]+[changed]+after[index+1:],{'features':{'cloud_depth':True}}))

 def test_post_float32_illustration_is_not_the_approved_source_payload(self):
  old,_=build(False);new,_=build(True);differences=0;max_ulp=0
  for before,after in zip(native_rows(old),native_rows(new)):
   illustrative=124.-(124.-before['vertices'][:,2])*2.2
   ulps=abs(after['vertices'][:,2].view(np.int32).astype(np.int64)-illustrative.view(np.int32))
   differences+=int(np.count_nonzero(ulps));max_ulp=max(max_ulp,int(ulps.max()))
   self.assertNotEqual(illustrative.tobytes(),after['vertices'][:,2].tobytes())
  self.assertEqual(differences,11032);self.assertEqual(max_ulp,2)


class AltitudeBlockTests(unittest.TestCase):
 def run_checks(self,flag,candidate,metadata_edit=None):
  g,md=build(candidate);v=np.concatenate([b['v'] for b in g.batches.values()])
  m={'features':{} if flag is None else {'cloud_depth':flag},'cloudSea':md,'materials':list(g.materials.values())}
  if metadata_edit:metadata_edit(m)
  checks=[];scope={'cloud':v,'m':m,'collision':[],'levels':{'L1':134.},'check':lambda name,ok,detail=None:checks.append((name,bool(ok)))}
  exec(altitude_block(),scope)
  self.assertGreaterEqual(len(checks),8,'Expected the full production cloud block')
  return checks

 def test_actual_altitude_block_accepts_both_intended_profiles(self):
  for flag,candidate in [(None,False),(False,False),(True,True)]:
   self.assertTrue(all(ok for _,ok in self.run_checks(flag,candidate)),(flag,candidate))

 def test_actual_altitude_block_rejects_implicit_opt_in_or_bad_metadata(self):
  for flag,candidate in [(None,True),(False,True),('true',True),(1,True),(True,False)]:
   self.assertFalse(all(ok for _,ok in self.run_checks(flag,candidate)),(flag,candidate))
  for edit in [lambda m:m['cloudSea']['depthRefinement'].__setitem__('factor',3.0),
               lambda m:m['cloudSea']['altitudeBounds'].__setitem__(0,0),
               lambda m:m['materials'][0].__setitem__('cloudBaseZ',110),
               lambda m:m['cloudSea'].__setitem__('maximumAnimatedAltitude',130)]:
   self.assertFalse(all(ok for _,ok in self.run_checks(True,True,edit)))


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path);args=parser.parse_args()
 suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 data=ROOT/'Assets/TreeTopYokocho/Data';native_state={'available':(data/'VisualMeshes.bytes').exists()}
 if (data/'WorldManifest.json').exists():
  try:
   md=json.loads((data/'WorldManifest.json').read_text());features=md.get('features',{})
   native_state.update(literalCloudDepth=isinstance(features,dict) and features.get('cloud_depth') is True,sourceVersion=md.get('version'),fixtureScope=md.get('fixtureScope'))
  except (OSError,ValueError,TypeError) as error:native_state['manifestError']=str(error)
 report={'status':'PASS' if result.wasSuccessful() else 'FAIL','testsRun':result.testsRun,
         'failures':[{'test':str(t),'details':error} for t,error in result.failures],
         'errors':[{'test':str(t),'details':error} for t,error in result.errors],
         'skipped':[{'test':str(t),'reason':reason} for t,reason in result.skipped],
         'baselineSha256':BASELINE_SHA,'sourceContextSha256':CONTEXT_SHA,'nativeCloudState':native_state,
         'scope':'Production-source isolated clouds, exact before/after native hashes, real production altitude AST block and supplied native cloud subset. No full-world generation, render, Unity shader execution, VR runtime or GPU performance claim.'}
 if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));return not result.wasSuccessful()


if __name__=='__main__':raise SystemExit(main())
