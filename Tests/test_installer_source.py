"""Offline contracts only: these do not execute Unity/Udon or claim scene install success."""
from pathlib import Path
import hashlib,json,re,unittest
from PIL import Image
from fontTools.ttLib import TTFont
from tree_sitter import Language,Parser
import tree_sitter_c_sharp
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'Assets/TreeTopYokochoEntrySystems'
SOURCE=(ASSETS/'Editor/EntrySystemsInstaller.cs').read_text()
class InstallerSourceTests(unittest.TestCase):
 def test_csharp_syntax(self):
  parser=Parser(Language(tree_sitter_c_sharp.language()))
  for path in ASSETS.rglob('*.cs'):
   self.assertFalse(parser.parse(path.read_bytes()).root_node.has_error,str(path))
 def test_no_core_builder_or_scene_replacement(self):
  self.assertNotIn('NewScene(',SOURCE);self.assertNotIn('BuildWorld(',SOURCE)
  self.assertNotIn('SaveScene(',SOURCE);self.assertNotIn('DeleteAsset("Assets/TreeTopYokocho/',SOURCE)
 def test_exact_core_manifest(self):
  self.assertIn('aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466',SOURCE)
  p=ASSETS/'Data/CoreCompatibility.json';self.assertIn(hashlib.sha256(p.read_bytes()).hexdigest(),SOURCE)
  rows=json.loads(p.read_text())['files'];self.assertEqual(len(rows),13);self.assertEqual(len({r['path'] for r in rows}),13)
 def test_preflight_before_mutation(self):
  self.assertLess(SOURCE.index('EntryPlazaBuilder.Preflight();'),SOURCE.index('EnsureFolder(AssetRoot'))
  self.assertLess(SOURCE.index('ValidateSky(oldSky);'),SOURCE.index('EnsureFolder(AssetRoot'))
  self.assertLess(SOURCE.index('ValidateCoreFiles();'),SOURCE.index('EnsureFolder(AssetRoot'))
 def test_repeated_install_returns_before_mutation(self):
  block=SOURCE.split('if (installed.Length == 1)',1)[1].split('// Every asset',1)[0]
  self.assertIn('ValidateExisting(installed[0]);',block);self.assertIn('return;',block)
  self.assertNotIn('Destroy',block);self.assertNotIn('CreateAsset',block)
 def test_owned_rollback(self):
  catch=SOURCE.split('            catch\n',1)[1].split('[MenuItem',1)[0]
  self.assertIn('RenderSettings.skybox = oldSky;',catch)
  self.assertIn('DestroyImmediate(root)',catch);self.assertIn('DeleteAsset(generated)',catch)
  self.assertIn('GenerateUniqueAssetPath',SOURCE)
 def test_music_empty_and_local_off(self):
  self.assertIn('return new AudioClip[0]',SOURCE);self.assertIn('".mp3"',SOURCE)
  self.assertIn('bgm.defaultOn = false',SOURCE);self.assertIn('audio.playOnAwake = false',SOURCE)
  self.assertNotIn('CanopyWind.wav',SOURCE)
 def test_meshes_persisted(self):
  self.assertIn('AssetDatabase.CreateAsset(mesh, generated + "/ControlLabel_"',SOURCE)
 def test_ascii_font(self):
  font=TTFont(ASSETS/'Fonts/YokochoEntryStatus.ttf');cmap=font.getBestCmap()
  self.assertTrue(set(range(32,127))<=set(cmap));self.assertLess(len(cmap),110)
  names=[n.toUnicode() for n in font['name'].names if n.nameID in (1,4,6)]
  self.assertTrue(all('Klee' not in n for n in names));self.assertTrue((ASSETS/'Fonts/OFL.txt').exists())
 def test_static_font_and_depth(self):
  importer=(ASSETS/'Editor/EntryAssetImporter.cs').read_text()
  self.assertIn('FontTextureCase.ASCII',importer);self.assertIn('font.fontNames = new string[0]',importer)
  shader=(ASSETS/'Shaders/EntryStatusText.shader').read_text()
  self.assertIn('ZTest LEqual',shader);self.assertNotIn('ZTest Always',shader)
 def test_label_atlas_provenance(self):
  report=json.loads((ROOT/'Docs/control_asset_provenance.json').read_text())
  for path,digest in report['outputs'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
  with Image.open(ASSETS/'Textures/entry_control_labels.png') as image:self.assertEqual(image.size,(960,1824))
  self.assertAlmostEqual(960/304,.60/.19,places=8)
 def test_no_new_lights_or_stations(self):
  self.assertNotIn('AddComponent<Light>',SOURCE);self.assertNotIn('AddComponent<VRCStation>',SOURCE)
  self.assertIn('clock.fillLight = null',SOURCE)
 def test_actual_interaction_transform_checks(self):
  self.assertIn('matches[0].recovery != recovery',SOURCE)
  self.assertIn('Quaternion.Angle(matches[0].destination.rotation',SOURCE)
  self.assertIn('Vector3 position = ButtonPosition(i)',SOURCE)
  self.assertIn('box.isTrigger',SOURCE);self.assertIn('box.center != Vector3.zero',SOURCE)
 def test_scene_audit_is_not_runtime_claim(self):
  self.assertIn('8b - Audit Installed Entry Systems',SOURCE)
  self.assertIn('Physics.SyncTransforms()',SOURCE)
  self.assertIn('Physics.OverlapCapsule',SOURCE)
  self.assertIn('Not Udon, multiplayer, avatar IK, visual-only geometry, bake or performance validation',SOURCE)
 def test_complete_control_geometry_inside_reviewed_panel(self):
  config=json.loads((ASSETS/'EntryPlaza/Data/EntryPlaza.json').read_text())['systemsControlAnchor']
  self.assertIn('135.50f - (index / 2) * .24f',SOURCE)
  self.assertIn('(index % 2 == 0 ? .36f : -.36f)',SOURCE)
  expected=[[-8+(.36 if i%2==0 else -.36),-31.59,135.5-(i//2)*.24] for i in range(6)]
  for actual,point in zip(config['buttonCenters'],expected):
   for a,b in zip(actual,point):self.assertAlmostEqual(a,b,places=6)
   for axis in [0,2]:
    half=config['buttonSize'][axis]/2
    self.assertGreaterEqual(point[axis]-half,config['usableMin'][axis])
    self.assertLessEqual(point[axis]+half,config['usableMax'][axis])
   for axis in range(3):
    half=config['buttonSize'][axis]/2
    self.assertGreaterEqual(point[axis]-half,config['reservedVolumeMin'][axis])
    self.assertLessEqual(point[axis]+half,config['reservedVolumeMax'][axis])
   self.assertLessEqual(point[1]+.019,config['reservedVolumeMax'][1])
  self.assertEqual(len(config['buttonCenters']),6)
 def test_front_print_is_not_mirrored(self):
  self.assertIn('new Vector2(1,low), new Vector2(0,low), new Vector2(0,high), new Vector2(1,high)',SOURCE)
 def test_dynamic_status_is_dark_and_bounded(self):
  self.assertIn('text.color = new Color(.10f, .16f, .13f)',SOURCE)
  self.assertIn('135.78f, -31.575f), .012f',SOURCE)
  self.assertIn('135.65f, -31.575f), .008f',SOURCE)
  self.assertIn('Bounds b = renderer.bounds',SOURCE)
  self.assertIn('b.size.x <= .01f || b.size.y <= .01f',SOURCE)
  self.assertIn('finally { text.text = original; }',SOURCE)
 def test_error_status_layout_is_not_silently_omitted(self):
  self.assertIn('BGM LOCAL / AUDIO ERROR\\nOFF > ON TO RETRY',SOURCE)
  self.assertIn('135.61f, 135.70f',SOURCE)
  self.assertIn('135.70f, 135.85f',SOURCE)
if __name__=='__main__':unittest.main(verbosity=2)
