import copy,hashlib,json,unittest,tempfile,shutil
from pathlib import Path
import shop_profile_contract as c

HERE=Path(__file__).resolve().parent
ASSETS=HERE.parent
BASE=HERE/'testdata/shop_profile_before_2_15.json'
class ShopProfileContract(unittest.TestCase):
 def setUp(self):
  profile=json.loads(BASE.read_text())
  if hashlib.sha256(BASE.read_bytes()).hexdigest()==c.PROFILE_SHA256:profile=c.authenticate_profile(profile)
  self.before=profile;self.after=copy.deepcopy(profile);self.after['materialGroups'].extend(c.load_fixture()['additions'])
 def test_exact_additions_restore_entire_old_profile(self):self.assertEqual(c.authenticate_profile(self.after),self.before)
 def test_any_old_setting_change_rejected(self):
  value=copy.deepcopy(self.after);value['materialGroups'][0]['shader']='NotApproved'
  with self.assertRaises(ValueError):c.authenticate_profile(value)
 def test_new_setting_or_extra_name_rejected(self):
  for action in ('extra','change','remove'):
   value=copy.deepcopy(self.after)
   if action=='extra':value['materialGroups'][-1]['names'].append('Night_Unapproved')
   elif action=='change':value['materialGroups'][-1]['floats'][0]['value']+=.1
   else:value['materialGroups'].pop()
   with self.assertRaises(ValueError):c.authenticate_profile(value)
 def test_city_dependency_literal_profile_gate(self):
  import city_roof_caps_contract as caps
  root=ASSETS
  source=HERE/'testdata/shop_profile_after_2_16.json'
  self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),c.OLD_PROFILE_SHA256)
  self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),c.PROFILE_SHA256)
  with tempfile.TemporaryDirectory() as directory:
   stage=Path(directory)
   fixture=stage/'Source/testdata'/c.FIXTURE_NAME;fixture.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/'testdata'/c.FIXTURE_NAME,fixture)
   for rel in ['Shaders/YokochoSurface.shader','Editor/YokochoWorldBuilder.cs','Editor/FantasyMaterialProfile.cs']:
    target=stage/'Assets/TreeTopYokocho'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    original=root/'Assets/TreeTopYokocho'/rel
    if rel=='Editor/YokochoWorldBuilder.cs':
     # Historical old/additive-profile cases need the exact historical builder,
     # not the new RPG runtime paired with an intentionally old profile.
     archived=HERE/'testdata/rpg_identity_legacy_builder_2_16.cs'
     if archived.is_file():original=archived
     self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),caps.BUILDER_SHA256)
    shutil.copyfile(original,target)
   target=stage/'Assets/TreeTopYokocho/Data/FantasyMaterials.json';target.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(BASE,target)
   self.assertEqual(caps.verified_dependencies(stage)['fantasyProfileSha256'],c.OLD_PROFILE_SHA256)
   with self.assertRaises(ValueError):caps.verified_dependencies(stage,shop_personality=True)
   with self.assertRaises(ValueError):caps.verified_dependencies(stage,shop_personality=1)
   shutil.copyfile(source,target)
   self.assertEqual(caps.verified_dependencies(stage,shop_personality=True)['fantasyProfileSha256'],c.PROFILE_SHA256)
   with self.assertRaises(ValueError):caps.verified_dependencies(stage)
 def test_unrelated_global_change_rejected(self):
  value=copy.deepcopy(self.after);value['unexpectedGlobal']=1
  with self.assertRaises(ValueError):c.authenticate_profile(value)
if __name__=='__main__':unittest.main(verbosity=2)
