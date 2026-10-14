"""Default-exact selective GLB image-encoding tests; isolated generated fixtures."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,inspect,io,json,sys,tempfile,unittest
import numpy as np
from PIL import Image
from pygltflib import GLTF2
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);OPTIONS=parser.parse_args()
sys.dont_write_bytecode=True

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
BEFORE=HERE/'testdata/shopfront_print/world_geometry_before.py'
BEFORE_SHA256='5117608965820c992f054b39f19c9f5f8524ab113ca39e1b9239806ad32a0e1e'
if not BEFORE.is_file() or hashlib.sha256(BEFORE.read_bytes()).hexdigest()!=BEFORE_SHA256:
 raise RuntimeError('Missing or changed immutable world geometry fixture: '+str(BEFORE))
old=load('world_geometry_old',BEFORE)
new=load('world_geometry_new',ROOT/'Source/world_geometry.py')
def digest(data):return hashlib.sha256(data).hexdigest()
def payload(g,index):
 v=g.bufferViews[index];return g.binary_blob()[v.byteOffset:v.byteOffset+v.byteLength]
def image_contract(g):
 result={}
 for mat in g.materials:
  refs={'base':mat.pbrMetallicRoughness.baseColorTexture,'normal':mat.normalTexture,'arm':mat.pbrMetallicRoughness.metallicRoughnessTexture,'occlusion':mat.occlusionTexture,'emission':mat.emissiveTexture}
  for kind,ref in refs.items():
   if ref is None:continue
   image=g.images[g.textures[ref.index].source];result[(mat.name,kind)]=(image.mimeType,payload(g,image.bufferView))
 return result

def build(module):
 g=module.Geometry()
 g.material('Print',(1,1,1),'shopfront_identity.png',emission=.28)
 g.material('Wood',(1,1,1),'wood.png',normal='normal.png',arm='arm.png')
 g.material('Alpha',(1,1,1),'leaf.png')
 for i,name in enumerate(g.materials):
  g.group='Fixture/'+name;g.quad([(i,0,0),(i+1,0,0),(i+1,0,1),(i,0,1)],name)
 g.compact();g.bake_mood([]);return g
REPORT={}
class SelectiveLosslessTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='lossless-fixture-');cls.p=Path(cls.tmp.name);rng=np.random.default_rng(28)
  for name,channels in [('shopfront_identity.png',3),('wood.png',3),('normal.png',3),('arm.png',3),('leaf.png',4)]:
   Image.fromarray(rng.integers(0,256,size=(96,128,channels),dtype=np.uint8)).save(cls.p/name)
  cls.hashes={p.name:digest(p.read_bytes()) for p in cls.p.glob('*.png')};cls.paths={};cls.models={}
  for label,mod,kwargs in [('old',old,{}),('default',new,{}),('empty',new,{'lossless_textures':()}),('irrelevant',new,{'lossless_textures':('not_used.png',)}),('lossless',new,{'lossless_textures':('shopfront_identity.png',)})]:
   g=build(mod);native_before=cls.p/(label+'_before.bytes');native_after=cls.p/(label+'_after.bytes');g.save_binary(native_before)
   path=cls.p/(label+'.glb');g.save_glb(path,cls.p,**kwargs);g.save_binary(native_after)
   cls.paths[label]=path;cls.models[label]=GLTF2().load_binary(path)
   if native_before.read_bytes()!=native_after.read_bytes():raise AssertionError('Exporter modified geometry '+label)
  REPORT['files']={k:{'sha256':digest(v.read_bytes()),'bytes':v.stat().st_size} for k,v in cls.paths.items()}
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()

 def test_default_empty_and_unused_opt_in_are_byte_exact(self):
  for key in ['default','empty','irrelevant']:self.assertEqual(self.paths['old'].read_bytes(),self.paths[key].read_bytes(),key)

 def test_only_named_atlas_encoding_changes(self):
  before=image_contract(self.models['old']);after=image_contract(self.models['lossless']);self.assertEqual(before.keys(),after.keys())
  for key,(mime,data) in before.items():
   new_mime,new_data=after[key]
   if key[0]=='Print':
    self.assertEqual(mime,'image/jpeg');self.assertEqual(new_mime,'image/png')
    decoded=Image.open(io.BytesIO(new_data));source=Image.open(self.p/'shopfront_identity.png')
    np.testing.assert_array_equal(np.asarray(decoded),np.asarray(source));self.assertEqual(decoded.size,source.size)
   else:self.assertEqual((mime,data),(new_mime,new_data),key)
  self.assertEqual(after[('Print','base')],after[('Print','emission')])

 def test_all_nonimage_buffer_payloads_are_exact(self):
  a=self.models['old'];b=self.models['lossless'];images={im.bufferView for im in a.images}
  self.assertEqual(len(a.bufferViews),len(b.bufferViews));self.assertEqual(len(a.accessors),len(b.accessors))
  for index in range(len(a.bufferViews)):
   if index not in images:self.assertEqual(payload(a,index),payload(b,index),index)
  for name in ['meshes','nodes','scenes','accessors','materials','textures','samplers']:
   self.assertEqual(json.loads(a.to_json()).get(name),json.loads(b.to_json()).get(name),name)

 def test_native_bytes_unchanged_across_paths(self):
  want=(self.p/'old_before.bytes').read_bytes()
  for path in self.p.glob('*.bytes'):self.assertEqual(want,path.read_bytes(),path.name)

 def test_source_texture_bytes_unchanged(self):
  self.assertEqual(self.hashes,{p.name:digest(p.read_bytes()) for p in self.p.glob('*.png')})

 def test_all_other_geometry_source_is_exact(self):
  for name,fn in vars(old.Geometry).items():
   if inspect.isfunction(fn) and name!='save_glb':self.assertEqual(inspect.getsource(fn),inspect.getsource(getattr(new.Geometry,name)),name)
  self.assertEqual(inspect.getsource(old.deduplicate_gltf_images),inspect.getsource(new.deduplicate_gltf_images))

 def test_max_texture_policy_is_not_bypassed(self):
  g=build(new);path=self.p/'capped.glb';g.save_glb(path,self.p,max_texture=64,lossless_textures=('shopfront_identity.png',))
  g=GLTF2().load_binary(path)
  for mime,data in image_contract(g).values():self.assertLessEqual(max(Image.open(io.BytesIO(data)).size),64)

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelectiveLosslessTests));REPORT['result']={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}
 OPTIONS.report.parent.mkdir(parents=True,exist_ok=True);OPTIONS.report.write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not result.wasSuccessful())
