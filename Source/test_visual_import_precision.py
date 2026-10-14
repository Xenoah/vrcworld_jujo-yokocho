"""Source guards for exact precision exceptions; not Unity compilation tests."""
from pathlib import Path
import json,shutil,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs'
class ImportPrecision(unittest.TestCase):
 def test_csharp_sources_parse(self):
  from tree_sitter import Language,Parser
  import tree_sitter_c_sharp
  parser=Parser(Language(tree_sitter_c_sharp.language()))
  for path in (BUILDER,BUILDER.with_name('MountainSeamNormals.cs')):
   self.assertFalse(parser.parse(path.read_bytes()).root_node.has_error,str(path))
 def test_cap_exception_exact_and_literal(self):
  s=BUILDER.read_text()
  self.assertIn('public bool city_roof_hidden_caps;',s)
  self.assertIn('manifest.features != null && manifest.features.city_roof_hidden_caps',s)
  self.assertIn('bool preserveCityGeometry = cityRoofHiddenCaps && group == "Landscape/DetailCityRoofs" && material == "DarkTimber";',s)
  self.assertIn('preserveCityGeometry ? ModelImporterMeshCompression.Off : ModelImporterMeshCompression.Low',s)
 def test_mountain_serializes_after_shared_normals_without_lossy_compression(self):
  s=BUILDER.read_text();block=s[s.index('if (mountainMeshes != null) {'):]
  self.assertLess(block.index('MountainSeamNormals.Apply(mountainMeshes);'),block.index('AssetDatabase.CreateAsset(mesh, mountainAssetPaths[key]);'))
  self.assertLess(block.index('ModelImporterMeshCompression.Off'),block.index('AssetDatabase.CreateAsset(mesh, mountainAssetPaths[key]);'))
  self.assertIn('if (!collision && !deferMountainAsset)',s)
 def test_collision_and_readability_unchanged(self):
  s=BUILDER.read_text();self.assertIn('materials, true);',s)
  self.assertIn('if (collision && (mountainSeamNormals || cityRoofHiddenCaps))',s)
  self.assertNotIn('UploadMeshData(true)',s)
  self.assertIn('vertices[i] = new Vector3(x, z, y);',s)
 def test_cap_precision_mutation_rejected_by_reviewed_digest(self):
  import city_roof_caps_contract as contract
  enabled=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text()).get('features',{}).get('shop_personality') is True
  contract.verified_dependencies(ROOT,shop_personality=enabled)
  with tempfile.TemporaryDirectory(prefix='precision-contract-') as temporary:
   out=Path(temporary)
   files={'Assets/TreeTopYokocho/'+rel for rel in ['Shaders/YokochoSurface.shader','Editor/YokochoWorldBuilder.cs','Data/FantasyMaterials.json','Editor/FantasyMaterialProfile.cs']}
   if BUILDER.with_name('VenueLightingProfile.cs').is_file():
    # Test-only complete source-reviewed runtime overlay, not a relaxed guard.
    # The unmodified positive must pass before the exact builder mutation runs.
    import rpg_runtime_compatibility as runtime
    files.update(runtime.load_oracle(ROOT)['dependencies'])
    files.update('Source/testdata/'+name for name in (runtime.BEFORE_NAME,runtime.ORACLE_NAME))
   for rel in sorted(files):
    path=out/rel;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,path)
   if enabled:
    from shop_profile_contract import FIXTURE_NAME
    fixture=out/'Source/testdata'/FIXTURE_NAME;fixture.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'Source/testdata'/FIXTURE_NAME,fixture)
   contract.verified_dependencies(out,shop_personality=enabled)
   path=out/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs'
   text=path.read_text().replace('preserveCityGeometry ? ModelImporterMeshCompression.Off','preserveCityGeometry ? ModelImporterMeshCompression.Low')
   path.write_text(text)
   with self.assertRaisesRegex(ValueError,'Editor/YokochoWorldBuilder.cs'):contract.verified_dependencies(out,shop_personality=enabled)
if __name__=='__main__':unittest.main()
