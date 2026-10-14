import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FoliagePreviewHookTests(unittest.TestCase):
 def test_insertion_before_fog_after_emission_gate(self):
  source=(ROOT/'Source/render_preview.py').read_text()
  gate=source.index("mat.node_tree.links.new(ray.outputs['Is Camera Ray']")
  hook=source.index("foliage_material_report=configure_foliage_emission")
  fog=source.index('surface_atmosphere=configure_surface_fog')
  self.assertLess(gate,hook);self.assertLess(hook,fog)
  self.assertEqual(source.count('foliage_material_report=configure_foliage_emission'),1)
  self.assertIn("'foliage_emission_approximation':foliage_material_report",source)
  self.assertIn("source_hashes['Source/foliage_preview.py']",source)
 def test_existing_runtime_emission_formula(self):
  s=(ROOT/'Assets/TreeTopYokocho/Shaders/YokochoFoliage.shader').read_text()
  self.assertIn('o.Emission=c*.035',s)
  self.assertIn('c=a.rgb*_Color.rgb*IN.color.rgb',s)
  self.assertIn('n.z*=IN.facing>0?1:-1',s)
if __name__=='__main__':unittest.main()
