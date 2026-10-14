"""Optional actual OIDN/EXR smoke tests on tiny synthetic diagnostic buffers.
These are tool/provenance checks, never visual evidence of the world.
"""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
AVAILABLE=all(importlib.util.find_spec(name) is not None for name in ('oidn','OpenEXR','PIL','numpy'))
@unittest.skipUnless(AVAILABLE,'Optional preview packages oidn/OpenEXR/Pillow/numpy required')
class DenoiserEvidence(unittest.TestCase):
 def setUp(self):
  import numpy as np
  from PIL import Image
  self.tmp=tempfile.TemporaryDirectory(prefix='denoise-proof-');self.root=Path(self.tmp.name);self.path=self.root/'tiny.png'
  rng=np.random.default_rng(12);pixels=np.uint8(np.clip(.5+rng.normal(0,.04,(32,32,3)),0,1)*255)
  Image.fromarray(pixels).save(self.path);self.original=self.path.read_bytes();self.metadata={'denoising':'none','denoising_scene_passes':False};self.write_meta()
 def tearDown(self):self.tmp.cleanup()
 def write_meta(self):self.path.with_suffix('.json').write_text(json.dumps(self.metadata))
 def run_filter(self,wrapper=False):
  script=ROOT/('Tools/denoise_render.py' if wrapper else 'Source/denoise_preview.py')
  return subprocess.run([sys.executable,str(script),str(self.path)],capture_output=True,text=True)
 def guides(self,shape=(32,32,3),invalid=False):
  import numpy as np,OpenEXR
  raw=self.root/'Raw';raw.mkdir(exist_ok=True)
  for kind in ('albedo','normal'):
   a=np.ones(shape,dtype=np.float32)*.5
   if kind=='normal':a[:]=[0,0,1]
   if invalid:a[0,0,0]=np.nan
   OpenEXR.File({}, {'RGB':a}).write(str(raw/(self.path.stem+'_'+kind+'_0001.exr')))
  self.metadata['denoising_scene_passes']=True;self.write_meta()
 def test_guided_raw_and_hashes(self):
  self.guides();result=self.run_filter();self.assertEqual(result.returncode,0,result.stderr)
  m=json.loads(self.path.with_suffix('.json').read_text());self.assertEqual((self.root/'Raw/tiny.png').read_bytes(),self.original)
  self.assertEqual(m['raw_render_sha256'],hashlib.sha256(self.original).hexdigest())
  self.assertEqual(m['denoised_render_sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
  self.assertEqual(set(m['denoising_guide_sha256']),{'albedo','normal'})
  self.assertIn('actual scene albedo/normal guides',m['denoising'])
 def test_double_filter_rejected(self):
  self.assertEqual(self.run_filter().returncode,0);before=self.path.read_bytes();raw=(self.root/'Raw/tiny.png').read_bytes()
  self.assertNotEqual(self.run_filter().returncode,0);self.assertEqual(self.path.read_bytes(),before);self.assertEqual((self.root/'Raw/tiny.png').read_bytes(),raw)
 def test_existing_raw_mismatch_preserved(self):
  (self.root/'Raw').mkdir();raw=self.root/'Raw/tiny.png';raw.write_bytes(b'prior evidence')
  self.assertNotEqual(self.run_filter().returncode,0);self.assertEqual(raw.read_bytes(),b'prior evidence');self.assertEqual(self.path.read_bytes(),self.original)
 def test_nonfinite_guide_rejected(self):
  self.guides(invalid=True);self.assertNotEqual(self.run_filter().returncode,0);self.assertEqual(self.path.read_bytes(),self.original)
 def test_wrong_shape_guide_rejected(self):
  self.guides(shape=(16,16,3));self.assertNotEqual(self.run_filter().returncode,0);self.assertEqual(self.path.read_bytes(),self.original)
 def test_compatibility_wrapper_preserves_provenance(self):
  self.assertEqual(self.run_filter(wrapper=True).returncode,0)
  self.assertEqual((self.root/'Raw/tiny.png').read_bytes(),self.original)
  self.assertIn('denoiser_script_sha256',json.loads(self.path.with_suffix('.json').read_text()))
if __name__=='__main__':unittest.main()
