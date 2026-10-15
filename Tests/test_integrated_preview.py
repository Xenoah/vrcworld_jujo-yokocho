"""Offline contracts for the complete source-preview assembly, not Unity execution."""
from pathlib import Path
import copy, hashlib, importlib.util, json, re, unittest
from tree_sitter import Language, Parser
import tree_sitter_c_sharp
ROOT=Path(__file__).resolve().parents[1]
EDITOR=ROOT/'Assets/TreeTopYokochoIntegration/Editor'
INSTALLER=(EDITOR/'OriginalPbrInstaller.cs').read_text()
BUILDER=(EDITOR/'IntegratedPreviewBuilder.cs').read_text()
IMPORTER=(EDITOR/'OriginalPbrImporter.cs').read_text()
spec=importlib.util.spec_from_file_location('original_plan',ROOT/'Tools/build_original_pbr_plan.py');plan=importlib.util.module_from_spec(spec);spec.loader.exec_module(plan)
class IntegratedSourceTests(unittest.TestCase):
 def test_all_csharp_grammar(self):
  parser=Parser(Language(tree_sitter_c_sharp.language()))
  for folder in ('TreeTopYokocho/Editor','TreeTopYokochoIntegration/Editor'):
   for p in (ROOT/'Assets'/folder).glob('*.cs'):self.assertFalse(parser.parse(p.read_bytes()).root_node.has_error,str(p))
 def test_exact_immutable_baseline(self):
  self.assertEqual(hashlib.sha256((ROOT/plan.MANIFEST).read_bytes()).hexdigest(),plan.MANIFEST_SHA)
 def test_roster_and_texture_only_stays_texture_only(self):
  m=json.loads((ROOT/plan.MANIFEST).read_text());before=copy.deepcopy(m);rows=plan.material_rows(m)
  self.assertEqual(m,before);self.assertEqual(len(rows),31);self.assertEqual(sum(x['calibrateParallax'] for x in rows),10)
  names={x['name']:x for x in rows};self.assertEqual([x['property'] for x in names['Food_Reed']['slots']],['_MainTex'])
  self.assertFalse(names['DeckCedar0']['calibrateParallax']);self.assertEqual(names['DeckCedar0']['replacementParallax'],0)
 def test_actual_unused_moss_definition(self):
  counts=plan.material_counts(ROOT);m=json.loads((ROOT/plan.MANIFEST).read_text());rows=plan.material_rows(m)
  self.assertEqual([r['name'] for r in rows if not counts[r['name']]],['Moss'])
  self.assertEqual(sum(counts.values()),1145)
  self.assertEqual(sum(counts[r['name']] for r in rows),523)
  self.assertEqual(sum(len(r['slots']) for r in rows),88)
 def test_rejects_unreviewed_parallax(self):
  m=json.loads((ROOT/plan.MANIFEST).read_text());m['materials'][0]['parallax']=.2
  with self.assertRaises(ValueError):plan.material_rows(m)
 def test_single_primary_entrypoint_and_cancel(self):
  self.assertIn('0 - Build or Complete Preview',BUILDER)
  self.assertLess(BUILDER.index('OriginalPbrInstaller.Preflight();'),BUILDER.index('YokochoWorldBuilder.Build();'))
  self.assertLess(BUILDER.index('OriginalPbrInstaller.Install();'),BUILDER.index('EntrySystemsInstaller.Install();'))
  self.assertIn('if (worlds.Length == 0) return;',BUILDER);self.assertIn('SaveCurrentModifiedScenesIfUserWantsTo()) return;',BUILDER)
  self.assertIn('OriginalPbrInstaller.Audit();',BUILDER);self.assertIn('EntrySystemsInstaller.AuditInstalled();',BUILDER)
 def test_preflight_and_current_core_audit_gate(self):
  self.assertLess(BUILDER.index('PreflightEntrySources();'),BUILDER.index('YokochoWorldBuilder.Build();'))
  self.assertLess(BUILDER.index('AuditCoreBeforeChanges();'),BUILDER.index('OriginalPbrInstaller.Install();'))
  self.assertLess(BUILDER.index('PreflightEntryScene(scene, worlds[0]);'),BUILDER.index('OriginalPbrInstaller.Install();'))
  self.assertIn('SceneManager.sceneCount != 1',BUILDER);self.assertIn('written.ToUniversalTime() < started',BUILDER)
  self.assertIn('lines.Count(x => x == "Errors: 0") != 1',BUILDER);self.assertIn('GetActiveScene().isDirty',BUILDER)
 def test_normal_gl_convention_is_not_reinterpreted(self):
  self.assertIn('importer.flipGreenChannel = false',IMPORTER);self.assertIn('importer.convertToNormalmap = false',IMPORTER)
  self.assertIn('!importer.flipGreenChannel && !importer.convertToNormalmap',INSTALLER)
  for channel in 'RGBA':
   self.assertIn(f'importer.swizzle{channel} = TextureImporterSwizzle.{channel}',IMPORTER)
   self.assertIn(f'importer.swizzle{channel} == TextureImporterSwizzle.{channel}',INSTALLER)
 def test_repeated_install_noop_before_mutation(self):
  self.assertLess(INSTALLER.index('if (markers.Length == 1)'),INSTALLER.index('EnsureFolder(Root + "/Generated")'))
  self.assertIn('ValidateExisting(plan, scene, core, markers[0]); return;',INSTALLER)
 def test_owned_rollback_only(self):
  block=INSTALLER.split('            catch\n',1)[1].split('        static void ValidatePair',1)[0]
  self.assertIn('pair.Key.sharedMaterials = pair.Value',block);self.assertIn('DeleteAsset(generated)',block)
  self.assertNotIn('DeleteAsset("Assets/TreeTopYokocho/',INSTALLER);self.assertNotIn('DeleteAsset(Root',INSTALLER)
 def test_clone_and_property_preservation(self):
  self.assertIn('new Material(originals[row.name])',INSTALLER)
  for phrase in ['original.shader == clone.shader','original.shaderKeywords','original.renderQueue == clone.renderQueue','GetTextureScale(property)','GetTextureOffset(property)','GetColor(property)','GetVector(property)']:
   self.assertIn(phrase,INSTALLER)
  self.assertNotIn('EnableKeyword(',INSTALLER);self.assertNotIn('DisableKeyword(',INSTALLER)
  self.assertNotIn('sharedMesh =',INSTALLER);self.assertNotIn('AddComponent<Light>',INSTALLER);self.assertNotIn('NewScene(',INSTALLER)
 def test_no_remaining_scan_bindings(self):
  self.assertIn('Active renderer still uses a historical scan texture',INSTALLER)
  self.assertIn('references.Length == row.expectedRendererCount && references.All(x => x == clone)',INSTALLER)
  self.assertIn('Partial/foreign original PBR marker',INSTALLER)
 def test_import_limits(self):
  for phrase in ['albedo && !terrain ? 2048 : 1024','TextureWrapMode.Repeat','importer.sRGBTexture = albedo','TextureImporterType.NormalMap','TextureImporterFormat.BC5','TextureImporterFormat.BC7','importer.mipmapEnabled = true']:
   self.assertIn(phrase,IMPORTER)
 def test_source_preview_not_runtime_claim(self):
  self.assertIn('No upload, Udon runtime, multiplayer, audio, light bake or headset validation',BUILDER)
  self.assertIn('unityRuntimeVerified = false',INSTALLER)
if __name__=='__main__':unittest.main()
