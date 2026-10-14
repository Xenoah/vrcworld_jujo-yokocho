"""Installed-project regression; no mutable sibling/staging tree is read."""
import hashlib,json,re,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def routing(profile):return {name:{key:value for key,value in g.items() if key!='names'} for g in profile['materialGroups'] for name in g['names']}
class AtlasWeave(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=json.loads((ROOT/'Docs/baselines/atlas_weave_revision.json').read_text())
  cls.profile=json.loads((ROOT/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text())
  manifest=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
  if manifest.get('features',{}).get('shop_personality') is True:
   sys.path.insert(0,str(ROOT/'Source'))
   from shop_profile_contract import verify_profile,authenticate_profile
   verify_profile(ROOT)
   cls.profile=authenticate_profile(cls.profile)
  cls.routes=routing(cls.profile)
 def test_only_approved_atlas_route_changed(self):
  self.assertEqual(sorted(self.routes),self.fixture['materialNames'])
  unchanged={n:v for n,v in self.routes.items() if n!='ShopfrontTextile'}
  self.assertEqual(digest(unchanged),self.fixture['unchangedMaterialRoutingSHA256'])
  self.assertEqual(self.routes['ShopfrontTextile'],self.fixture['ShopfrontTextileRouting'])
  self.assertEqual(self.routes['DarkTimber'],self.fixture['DarkTimberRouting'])
  values=lambda n:{x['name']:x['value'] for x in self.routes[n]['floats']}
  self.assertEqual(values('ShopfrontTextile')['_WeaveScale'],4096)
  self.assertEqual(values('CityWovenBanner')['_WeaveScale'],96)
  for i in range(8):self.assertEqual(values(f'Noren{i}')['_WeaveScale'],96)
 def test_shader_body_preserved(self):
  shader=(ROOT/'Assets/TreeTopYokocho/Shaders/YokochoCloth.shader').read_text()
  self.assertIn('Range(8,4096)) = 96',shader)
  body=re.sub(r'^\s*_WeaveScale\s*\([^\n]*$', '<WEAVE_PROPERTY>',shader,flags=re.M)
  self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),self.fixture['unchangedShaderBodySHA256'])
  self.assertIn('1.0-smoothstep(.20,.50,footprint)',shader)
 def test_recorded_filter_attenuation_is_reproducible(self):
  evidence=self.fixture['footprintEvidence']
  frequency=evidence['newCyclesPerMetrePercentiles10_50_90'][1][0]
  previous=1
  for row in evidence['filterSamples']:
   x=frequency*row['worldPixelFootprintMM']/1000
   t=min(1,max(0,(x-.2)/.3));fraction=1-t*t*(3-2*t)
   self.assertAlmostEqual(fraction,row['remainingNormalAmplitudeFractionPrincipal'])
   self.assertLessEqual(fraction,previous);previous=fraction
  self.assertEqual(previous,0)
if __name__=='__main__':unittest.main()
