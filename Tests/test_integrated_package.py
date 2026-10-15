"""Pure temporary-directory package tests; not a Unity build."""
from pathlib import Path
import hashlib, importlib.util, json, tempfile, unittest, zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('integrated_package', ROOT/'Tools/package_integrated_preview.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class PackageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);self.root=self.base/'project';self.root.mkdir()
 def write(self,name,data='fixture'):
  f=self.root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(data);return f
 def complete(self):
  for name in ('Source/TreeTopYokocho.glb','Source/run_checks.py','Tools/run_integrated_checks.py','Assets/TreeTopYokocho/Data/GeometryShards.json',
   'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes.gz','Assets/TreeTopYokocho/Data/WorldManifest.json'):self.write(name)
  maps=[]
  for i in range(16):
   name=f'Assets/TreeTopYokochoOriginalPbr/Textures/PBR/map{i}.png';self.write(name);maps.append(dict(path=name,sha256=p.sha(b'fixture')))
  plan=json.dumps(dict(maps=maps));self.write('Assets/TreeTopYokochoOriginalPbr/Data/OriginalPbrPlan.json',plan)
  self.write('Assets/TreeTopYokochoIntegration/Editor/OriginalPbrInstaller.cs',f'public const string ApprovedPlanSha256 = "{p.sha(plan.encode())}";')
  self.write('Docs/ORIGINAL_PBR_REVIEW.json',json.dumps(dict(sourcePreviewAccepted=True,unityRuntimeVerified=False)))
  self.write('Docs/integrated-source-validation.json',json.dumps(dict(status='PASS',verifiedInventory={n:p.sha(f.read_bytes()) for n,f in p.inventory(self.root).items()})))
 def test_exclusions_and_keep_release_glb(self):
  for path in ('Assets/TreeTopYokocho/Data/VisualMeshes.bytes','Assets/TreeTopYokochoOriginalPbr/Generated/Materials/x.mat','Assets/TreeTopYokochoOriginalPbr/Generated.meta','Preview/Raw/x.png','Source/__pycache__/x.pyc','Source/x.blend','Preview/x.html'):
   self.write(path)
  self.write('Source/TreeTopYokocho.glb');self.write('Preview/OriginalPbr/actual_trunk.png');self.write('Preview/world_authored/Raw/Blender_deck_walk.png')
  self.assertEqual(set(p.inventory(self.root)),{'Source/TreeTopYokocho.glb','Preview/OriginalPbr/actual_trunk.png','Preview/world_authored/Raw/Blender_deck_walk.png'})
 def test_no_symlink_data(self):
  outside=self.base/'outside';outside.write_text('not permitted');f=self.root/'Source/link';f.parent.mkdir();f.symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'symlinks'):p.inventory(self.root)
 def test_no_root_symlink_data(self):
  outside=self.base/'outside';outside.write_text('not permitted');(self.root/'README.md').symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'symlinks'):p.inventory(self.root)
 def test_source_missing_fails(self):
  with self.assertRaisesRegex(ValueError,'Missing required'):p.package(self.root,self.base/'x.zip')
 def test_unfrozen_or_changed_plan_fails(self):
  self.complete();self.write('Assets/TreeTopYokochoIntegration/Editor/OriginalPbrInstaller.cs','ApprovedPlanSha256 = "UNFROZEN";')
  with self.assertRaisesRegex(ValueError,'not frozen'):p.package(self.root,self.base/'x.zip')
 def test_changed_map_fails(self):
  self.complete();self.write('Assets/TreeTopYokochoOriginalPbr/Textures/PBR/map0.png','changed')
  with self.assertRaisesRegex(ValueError,'changed authored'):p.package(self.root,self.base/'x.zip')
 def test_inside_output_rejected(self):
  with self.assertRaisesRegex(ValueError,'outside'):p.package(self.root,self.root/'x.zip')
 def test_source_changed_after_verification_rejected(self):
  self.complete();self.write('Source/run_checks.py','changed')
  with self.assertRaisesRegex(ValueError,'since integrated verification'):p.package(self.root,self.base/'x.zip')
 def test_noncode_added_after_verification_rejected(self):
  self.complete();self.write('Assets/OldCore/noncode.jpg','unverified image')
  with self.assertRaisesRegex(ValueError,'since integrated verification'):p.package(self.root,self.base/'x.zip')
 def test_noncode_changed_after_verification_rejected(self):
  self.write('Assets/OldCore/noncode.jpg','first image');self.complete();self.write('Assets/OldCore/noncode.jpg','unverified image')
  with self.assertRaisesRegex(ValueError,'since integrated verification'):p.package(self.root,self.base/'x.zip')
 def test_crc_hashes_deterministic_source_preview(self):
  self.complete();a=p.package(self.root,self.base/'a.zip');b=p.package(self.root,self.base/'b.zip')
  self.assertEqual(a['sha256'],b['sha256']);self.assertTrue(a['crcPass']);self.assertTrue(a['everyFileHashMatches'])
  with zipfile.ZipFile(self.base/'a.zip') as z:
   identity=json.loads(z.read('TreeTopYokocho/ARCHIVE_IDENTITY.json'))
   self.assertFalse(identity['compiledWorld']);self.assertFalse(identity['unityRuntimeVerified'])
   for name,h in identity['files'].items():self.assertEqual(p.sha(z.read('TreeTopYokocho/'+name)),h)
if __name__=='__main__':unittest.main()
