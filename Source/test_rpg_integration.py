"""Actual generated v2.17 identity metadata, never a screenshot-only approval."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class IntegratedIdentityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.manifest=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
 def test_literal_revision_flags(self):
  if 'venue_projecting_signs' in self.manifest['features']:
   import projecting_sign_contract as signs
   self.assertEqual(signs.validate_gate(self.manifest),[])
  elif 's05_pendant_refinement' in self.manifest['features']:
   import s05_pendant_contract as pendant
   self.assertEqual(pendant.validate_gate(self.manifest),[])
   self.assertEqual(self.manifest['version'],'2.18.0')
  else:self.assertEqual(self.manifest['version'],'2.17.0')
  for name in ('shop_rpg_identity','venue_lighting_identity'):
   self.assertIs(type(self.manifest['features'][name]),bool)
 def test_all_actual_shop_names_and_identity_claims(self):
  m=self.manifest
  if not m['features']['shop_rpg_identity']:
   self.assertNotIn('shopRpgIdentity',m);return
  from rpg_shop_identities import IDENTITIES
  names=[dict(id=f'S{i+1:02d}',displayName=IDENTITIES[i]['name']) for i in range(8)]
  self.assertEqual(m['shopRpgIdentity']['names'],names)
  self.assertEqual([dict(id=s['id'],displayName=s['displayName']) for s in m['shopPersonality']['shops']],names)
  p=m['shopRpgIdentity'];digest=lambda rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
  self.assertEqual(p['sourceSha256'],digest('Source/rpg_shop_identities.py'))
  self.assertEqual(p['fontManifestSha256'],digest('Source/fonts/rpg-fonts.json'))
  self.assertEqual(p['atlasSha256'],{n:digest('Assets/TreeTopYokocho/Textures/'+n) for n in ('food_venue_signs.png','nightlife_signs.png')})
 def test_actual_lighting_profile_binding(self):
  import venue_lighting as lighting
  p=lighting.load_profile(ROOT/lighting.PROFILE_RELATIVE) if self.manifest['features']['venue_lighting_identity'] else None
  lighting.validate_manifest(self.manifest,p)
if __name__=='__main__':unittest.main()
