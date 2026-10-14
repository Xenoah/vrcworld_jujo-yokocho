"""Portable isolated contracts: no world build, external writes, or rendering.

python Source/test_shopfront_print.py --report Docs/shopfront_print_validation.json
Optional --project overrides the default project root. Immutable fixtures live
under Source/testdata/shopfront_print. Exact Noto CJK font files are required;
see that fixture directory's README. Missing/mismatched fonts fail, never skip.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,inspect,json,os,random,sys,tempfile,time,unittest
from unittest import mock
import numpy as np
from PIL import Image,ImageDraw
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--project',type=Path,default=HERE.parent)
parser.add_argument('--report',type=Path,required=True)
OPTIONS,UNIT_ARGS=parser.parse_known_args()
ROOT=HERE.parent
sys.path.append(str(OPTIONS.project/'Source'))
from world_geometry import Geometry

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
FIXTURE_DIR=HERE/'testdata/shopfront_print'
FIXTURE_HASHES={
 'shopfront_identity_before.py':'9938fd33ab1d64283e21da5614e839ea55e31fe76c0a702b77a5409755c8b1cb',
}
# The historical PNG need not be packaged: a fresh frozen-source bake must
# reproduce its exact shipped digest before any candidate pixel proof runs.
SHIPPED_ATLAS_SHA256='8afee5ad6ca5368d89499af353b0829a15f54a56131aa79cde298a5fc572ac85'
FONT_HASHES={
 '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc':'1505ee3b9c0890fae6302ee0e9c6fd74d690f4a55a6ace1d9944f3f6352d622d',
 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc':'b76b0433203017ca80401b2ee0dd69350349871c4b19d504c34dbdd80541690a',
}
# Validate before importing the historical generator: these are immutable
# review fixtures, not an alternate source of editable production behavior.
for name,want in FIXTURE_HASHES.items():
 path=FIXTURE_DIR/name
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
  raise RuntimeError('Missing or changed immutable shopfront print fixture: '+str(path))
for name,want in FONT_HASHES.items():
 path=Path(name)
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
  raise RuntimeError('Exact shopfront raster proof requires the documented Noto CJK font: '+name+' (sha256 '+want+'). See Source/testdata/shopfront_print/README.md; pixel proofs are not skipped.')
base=load('shopfront_before_print',FIXTURE_DIR/'shopfront_identity_before.py')
new=load('shopfront_after_print',HERE/'shopfront_identity.py')
FONT_DIR=Path('/usr/share/fonts/opentype/noto')
SERIF=FONT_DIR/'NotoSerifCJK-Bold.ttc'
SANS=FONT_DIR/'NotoSansCJK-Regular.ttc'
LAYOUT=json.loads((OPTIONS.project/'Source/layout.reference.json').read_text())['shops']
MANIFEST=json.loads((OPTIONS.project/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
M=dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',iron='Iron')
REPORT={'scope':'Isolated authored print-layer and shop identity geometry tests; no Unity/VRChat runtime test', 'source':{},'bakes':{},'geometry':{},'preservation':{},'immutable_fixtures':FIXTURE_HASHES,'shipped_atlas_sha256':SHIPPED_ATLAS_SHA256,'required_font_sha256':FONT_HASHES}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def build_geometry(mod,idx,staff,craft):
 g=Geometry();g.group='Shops/'+LAYOUT[idx]['id'];g.materials={m['name']:copy.deepcopy(m) for m in MANIFEST['materials']}
 def P(*p):return np.asarray(p,float)
 def B(x,y,z,w,d,h,ma):g.box(P(x,y,z),(w,d,h),ma)
 s=LAYOUT[idx];mod.add_shopfront_identity(g,P,B,s['width'],s['depth'],idx,M,staff_entry=staff,noren_craft=craft)
 h=hashlib.sha256()
 for key,b in g.batches.items():
  h.update(canonical(key).encode())
  for k in ('v','f','uv'):
   a=np.asarray(b[k]);h.update(str((a.shape,a.dtype.str)).encode());h.update(a.tobytes())
 h.update(canonical(g.materials).encode())
 return h.hexdigest(),sum(len(b['f']) for b in g.batches.values())

def bake(mod,out,enabled=None,font=None,trace=None):
 center=mod._center_text
 def observed(d,pos,text,font,fill,max_width=None):
  if trace is not None:trace.append((pos,text,str(font.path),font.size,fill,max_width))
  return center(d,pos,text,font,fill,max_width)
 with mock.patch.object(mod,'_center_text',observed):
  args={} if enabled is None else {'antialias_print':enabled}
  return mod.make_shopfront_atlas(out,font,**args)

class ShopfrontPrintTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='shopfront-print-')
  cls.path=Path(cls.tmp.name);cls.traces={};cls.images={};cls.paths={}
  for key,mod,on in [('original',base,None),('disabled',new,None),('enabled',new,True),('repeat',new,True)]:
   cls.traces[key]=[];t=time.perf_counter();path=bake(mod,cls.path/key,on,trace=cls.traces[key]);cls.paths[key]=path
   if key=='original' and sha(path)!=SHIPPED_ATLAS_SHA256:
    raise AssertionError('Frozen original generator does not reproduce the immutable shipped atlas SHA-256; do not run candidate pixel proofs against a drifted baseline.')
   cls.images[key]=np.asarray(Image.open(path)).copy()
   REPORT['bakes'][key]={'sha256':sha(path),'seconds':round(time.perf_counter()-t,4),'bytes':path.stat().st_size}
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()

 def test_immutable_fixture_files_are_pinned(self):
  for name,want in FIXTURE_HASHES.items():self.assertEqual(sha(FIXTURE_DIR/name),want)

 def test_original_shipped_atlas_reproduced_exactly(self):
  self.assertEqual(sha(self.paths['original']),SHIPPED_ATLAS_SHA256)

 def test_disabled_path_stays_byte_exact(self):
  self.assertEqual(sha(self.paths['disabled']),sha(self.paths['original']))

 def test_enabled_is_deterministic_and_same_atlas_format(self):
  self.assertEqual(sha(self.paths['enabled']),sha(self.paths['repeat']))
  self.assertNotEqual(sha(self.paths['enabled']),sha(self.paths['original']))
  for path in self.paths.values():
   with Image.open(path) as im:self.assertEqual(im.size,(2048,2048));self.assertEqual(im.mode,'RGB')
  self.assertEqual(new.ATLAS_NAME,base.ATLAS_NAME);self.assertEqual(new.ATLAS_SIZE,base.ATLAS_SIZE)

 def test_identical_identity_palette_and_wording(self):
  self.assertEqual(base.IDENTITIES,new.IDENTITIES)
  self.assertEqual(len(new.IDENTITIES),8)
  REPORT['source']['identities_sha256']=hashlib.sha256(canonical(new.IDENTITIES).encode()).hexdigest()

 def test_exact_unchanged_paths_layout_and_geometry_source(self):
  names=[name for name,obj in vars(base).items() if inspect.isfunction(obj) and obj.__module__==base.__name__ and name!='make_shopfront_atlas']
  for name in names:
   before=inspect.getsource(getattr(base,name));after=inspect.getsource(getattr(new,name));self.assertEqual(before,after,name)
   REPORT['source'][name]=hashlib.sha256(after.encode()).hexdigest()

 def test_every_text_call_has_same_wording_font_size_and_position(self):
  self.assertEqual(self.traces['original'],self.traces['enabled'])
  REPORT['preservation']['identical_text_draw_calls']=len(self.traces['enabled'])

 def test_empty_layer_leaves_all_background_pixels_exact(self):
  pixels=np.random.default_rng(91).integers(0,256,size=(16,24,3),dtype=np.uint8)
  tile=Image.fromarray(pixels);draw=new._PrintLayer(tile)
  self.assertEqual(draw.layer.size,(24*8,16*8))
  self.assertEqual(draw.layer.mode,'RGBA')
  self.assertEqual(draw.layer.getchannel('A').getextrema(),(0,0))
  np.testing.assert_array_equal(np.asarray(draw.composite(tile)),pixels)

 def test_literal_opt_in_only(self):
  image=Image.new('RGB',(10,10))
  for off in [False,None,0,1,'true',np.bool_(True),[],{}]:self.assertNotIsInstance(new._print_draw(image,off),new._PrintLayer)
  self.assertIsInstance(new._print_draw(image,True),new._PrintLayer)

 def test_font_fallback_existing_bake_survives_without_fonts(self):
  out=self.path/'fontless';out.mkdir(exist_ok=True);path=out/new.ATLAS_NAME
  path.write_bytes(self.paths['original'].read_bytes());old=sha(path);exists=Path.exists
  def no_fonts(p):return False if p.suffix in ('.ttc','.otf','.ttf') else exists(p)
  with mock.patch.object(Path,'exists',no_fonts):
   self.assertEqual(new.make_shopfront_atlas(out,antialias_print=True),path)
   self.assertEqual(sha(path),old)
   with self.assertRaises(FileNotFoundError):new.make_shopfront_atlas(self.path/'missing',antialias_print=True)

 def test_supplied_font_and_sign_font_fallback_order_match(self):
  class Stop(Exception):pass
  exists=Path.exists
  for disabled_serif in [False,True]:
   seen=[]
   def first_font(path,size):seen.append((str(path),size));raise Stop()
   def hide_serif(p):return False if disabled_serif and p==SERIF else exists(p)
   for mod in [base,new]:
    with mock.patch.object(Path,'exists',hide_serif),mock.patch.object(mod,'_font',first_font),self.assertRaises(Stop):
     mod.make_shopfront_atlas(self.path/'font-order',SANS)
   self.assertEqual(seen[0],seen[1]);self.assertEqual(seen[1][0],str(SANS if disabled_serif else SERIF))

 def test_all_shop_mesh_payloads_and_uvs_are_exact(self):
  for idx in range(8):
   for staff in [False,True]:
    for craft in [False,True]:
     a=build_geometry(base,idx,staff,craft);b=build_geometry(new,idx,staff,craft);self.assertEqual(a,b,(idx,staff,craft))
     REPORT['geometry'][f'{idx}_staff_{staff}_crafted_{craft}']={'sha256':a[0],'triangles':a[1]}

 def test_no_global_rng_mutation(self):
  before_py=random.getstate();before_np=np.random.get_state()
  new.make_shopfront_atlas(self.path/'rng',antialias_print=True)
  self.assertEqual(random.getstate(),before_py);after=np.random.get_state()
  self.assertEqual(before_np[0],after[0]);np.testing.assert_array_equal(before_np[1],after[1]);self.assertEqual(before_np[2:],after[2:])

 def test_base_texture_untouched_outside_original_and_new_print(self):
  masks=[];original_composite=new._PrintLayer.composite
  def capture(layer,tile):
   masks.append(np.asarray(layer.layer.resize(layer.size,layer.resample).getchannel('A')).copy())
   return original_composite(layer,tile)
  atlas_mask=np.zeros((2048,2048),bool)
  with mock.patch.object(new._PrintLayer,'composite',capture):
   for scale in [1,new._PrintLayer.scale]:
    masks.clear()
    with mock.patch.object(new._PrintLayer,'scale',scale):new.make_shopfront_atlas(self.path/f'mask{scale}',antialias_print=True)
    self.assertEqual(len(masks),72)
    for idx in range(8):
     origins=[(0,idx*256),(0,idx*256+128),*[(1024+j*112,idx*256) for j in range(6)],(1792,idx*256)]
     for k,(x,y) in enumerate(origins):
      mask=masks[idx*9+k];h,w=mask.shape;atlas_mask[y:y+h,x:x+w]|=mask>0
  changed=np.any(self.images['original']!=self.images['enabled'],axis=2)
  self.assertEqual(int(np.count_nonzero(changed&~atlas_mask)),0)
  REPORT['preservation'].update({'unprinted_pixels':int(np.count_nonzero(~atlas_mask)), 'changed_unprinted_pixels':int(np.count_nonzero(changed&~atlas_mask)), 'changed_total_pixels':int(changed.sum()),'total_pixels':int(changed.size),'background_exact':True})

 def test_original_repairs_and_capillary_wear_are_exact(self):
  for idx in range(8):
   row=idx*256
   boxes=[(8,row+137,18,row+244),(1004,row+137,1016,row+244)]
   if idx in [0,3,5]:boxes.append((80,row+80,120,row+109))
   for x0,y0,x1,y1 in boxes:np.testing.assert_array_equal(self.images['original'][y0:y1,x0:x1],self.images['enabled'][y0:y1,x0:x1])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ShopfrontPrintTests))
 REPORT['result']={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}
 OPTIONS.report.parent.mkdir(parents=True,exist_ok=True)
 OPTIONS.report.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n')
 sys.exit(not result.wasSuccessful())
