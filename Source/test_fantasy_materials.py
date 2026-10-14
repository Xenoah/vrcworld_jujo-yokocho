"""Profile and editor routing source guards. No Unity compiler/runtime claim."""
from pathlib import Path
import copy,json,sys,unittest
from fantasy_materials import validate_profile,load_profile,groups_by_name,PROFILE_RELATIVE
ROOT=Path(__file__).resolve().parents[1]
class FantasyMaterials(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.materials=json.loads((ROOT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())['materials']
        cls.profile=load_profile(ROOT,cls.materials)
    def test_unique_existing_routing(self):
        groups=groups_by_name(self.profile)
        self.assertEqual(len(groups),sum(len(g['names']) for g in self.profile['materialGroups']))
        for name in ['SignAtlas','MenuAtlas','AviationRed','WarmWindow','TownLights']:self.assertNotIn(name,groups)
    def test_bad_schema(self):
        for value in [True,0,2,'1',None]:
            p=copy.deepcopy(self.profile);p['schema']=value
            with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_duplicate_unknown_materials(self):
        for name in ['DefinitelyMissing',self.profile['materialGroups'][0]['names'][0]]:
            p=copy.deepcopy(self.profile);p['materialGroups'][0]['names'].append(name)
            with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_nonfinite_values(self):
        for value in [float('nan'),float('inf'),True,'1']:
            p=copy.deepcopy(self.profile);p['materialGroups'][0]['floats'][0]['value']=value
            with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_duplicate_float_and_vector(self):
        p=copy.deepcopy(self.profile);g=p['materialGroups'][0];g['vectors']=[{'name':g['floats'][0]['name'],'value':[1,2,3,4]}]
        with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_bad_keyword(self):
        p=copy.deepcopy(self.profile);p['sky']['keywords']=['_UNKNOWN']
        with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_malformed_containers(self):
        for field in ('floats','vectors','keywords'):
            for value in (None,{},'not-an-array',True,4):
                p=copy.deepcopy(self.profile);p['materialGroups'][0][field]=value
                with self.assertRaises(ValueError):validate_profile(p,self.materials)
            for value in (None,[],True,4):
                p=copy.deepcopy(self.profile);p['materialGroups'][0][field]=[value]
                with self.assertRaises(ValueError):validate_profile(p,self.materials)
        for value in ([],{},None,True):
            p=copy.deepcopy(self.profile);p['materialGroups'][0]['shader']=value
            with self.assertRaises(ValueError):validate_profile(p,self.materials)
        for value in ('true',1,None,[]):
            p=copy.deepcopy(self.profile);p['materialGroups'][0]['textureKeywords']=value
            with self.assertRaises(ValueError):validate_profile(p,self.materials)
    def test_editor_preflight_before_return(self):
        s=(ROOT/'Assets/TreeTopYokocho/Editor/FantasyMaterialProfile.cs').read_text()
        self.assertIn('PreflightShader("TreeTopYokocho/" + group.shader, group);',s)
        self.assertLess(s.index('PreflightShader("TreeTopYokocho/BlueHourSky", profile.sky);'),s.index('return profile;'))
        self.assertIn('finally { if (temporary != null) UnityEngine.Object.DestroyImmediate(temporary); }',s)
        self.assertGreaterEqual(s.count('HasProperty(entry.name)'),4)
    def test_csharp_syntax(self):
        from tree_sitter import Language,Parser
        import tree_sitter_c_sharp
        parser=Parser(Language(tree_sitter_c_sharp.language()))
        for name in ['FantasyMaterialProfile.cs','YokochoWorldBuilder.cs']:
            self.assertFalse(parser.parse((ROOT/'Assets/TreeTopYokocho/Editor'/name).read_bytes()).root_node.has_error,name)
    def test_builder_order_and_disabled_gate(self):
        s=(ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
        self.assertIn('manifest.features != null && manifest.features.fantasy_materials',s)
        self.assertLess(s.index('FantasyMaterialProfile.Load'),s.index('EditorSceneManager.NewScene'))
        self.assertLess(s.index('BindTexture(material'),s.index('FantasyMaterialProfile.Apply(material'))
        self.assertLess(s.index('FantasyMaterialProfile.Apply(material'),s.index('AssetDatabase.CreateAsset(material'))
        self.assertIn('material.HasProperty("_Parallax") && !string.IsNullOrEmpty(m.height)',s)
        self.assertIn('if (fantasy != null) FantasyMaterialProfile.Apply(sky, fantasy.sky);',s)
    def test_every_property_declared(self):
        for group in self.profile['materialGroups']+[dict(self.profile['sky'],shader='Sky')]:
            text=(ROOT/'Assets/TreeTopYokocho/Shaders'/('Yokocho'+group['shader']+'.shader')).read_text().split('SubShader')[0]
            for entry in group.get('floats',[])+group.get('vectors',[]):self.assertIn(entry['name'],text)
if __name__=='__main__':unittest.main()
