"""Bounded static lighting unit tests, including real authored venue geometry.

No Unity bake, runtime, FPS, retinal glare or physical illuminance claims.
Run python Source/test_venue_lighting.py. Actual full payload audit is separate.
"""
from pathlib import Path
import copy
import hashlib
import json
import random
import unittest
import numpy as np
import venue_lighting as vl

ROOT = Path(__file__).resolve().parent.parent


class VenueLightingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = vl.load_profile(ROOT / vl.PROFILE_RELATIVE)
        from test_food_venues import fixture
        from test_nightlife_venues import make
        old = json.loads((ROOT/'Source/testdata/shop_personality_before_2_15.json').read_text())['manifest']['materials']
        cls.venues = {}
        for i in range(8):
            if i in (0, 1, 2, 4, 7):
                sample = fixture(old, i); g, result = sample['g'], sample['report']
            else:
                g, result = make(i)
            cls.venues[f'S{i+1:02d}'] = (g, result)

    def mutated(self, callback):
        p = copy.deepcopy(self.profile); callback(p)
        with self.assertRaises((ValueError, TypeError)): vl.validate_profile(p)

    def test_draft_profile_roster_and_budget(self):
        self.assertEqual(sum(len(s['fixtures']) for s in self.profile['shops']), 15)
        self.assertEqual(sum(len(s['emitters']) for s in self.profile['shops']), 12)
        self.assertEqual([s['id'] for s in self.profile['shops']], list(vl.SHOP_IDS))
        for shop in self.profile['shops']:
            old = sum(f['strength'] for f in shop['fixtures']) * vl.luminance([1,.52,.18])
            new = sum(f['strength']*f['intensityMultiplier']*vl.luminance(f['color']) for f in shop['fixtures'])
            self.assertTrue(.8 <= new/old <= 1.28)
            self.assertTrue(any(f['role'] in ('key','task') for f in shop['fixtures']))

    def test_nonfinite_negative_and_hdr_colors_rejected(self):
        for value in (float('nan'), float('inf'), -1, 1.01, True, '1'):
            with self.subTest(value=value):
                self.mutated(lambda p: p['shops'][0]['fixtures'][0]['color'].__setitem__(0,value))

    def test_invalid_schema_version_feature_rejected(self):
        for key, value in [('schema',True),('schema',2),('version','future'),('feature','other')]:
            self.mutated(lambda p:p.__setitem__(key,value))

    def test_literal_feature_and_dependency(self):
        for value in (1,0,'true',None,[]):
            with self.assertRaises(ValueError):vl.feature_enabled({vl.FEATURE:value,'shop_personality':True})
        with self.assertRaises(ValueError):vl.feature_enabled({vl.FEATURE:True})
        self.assertFalse(vl.feature_enabled({}))
        self.assertFalse(vl.feature_enabled({vl.FEATURE:False}))
        self.assertTrue(vl.feature_enabled({vl.FEATURE:True,'shop_personality':True}))

    def test_existing_indices_and_counts_are_strict(self):
        self.mutated(lambda p:p['shops'][0]['fixtures'].pop())
        self.mutated(lambda p:p['shops'][0]['fixtures'][0].update(manifestIndex=87))
        self.mutated(lambda p:p['shops'].reverse())

    def test_global_legacy_constants_cannot_be_tuned(self):
        self.mutated(lambda p:p.update(legacyUnityColor=[1,1,1]))
        self.mutated(lambda p:p.update(previewBaseEnergy=111))
        self.mutated(lambda p:p.update(rangeMultiplier=1.26))
        self.mutated(lambda p:p.update(bounceIntensity=1.7))

    def test_static_emission_and_point_budget_caps(self):
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(emission=1.01))
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(breath=.01))
        self.mutated(lambda p:p['shops'][0]['fixtures'][0].update(intensityMultiplier=1.16))
        self.mutated(lambda p:p['shops'][3]['emitters'][1].update(emission=.41))

    def test_neutral_key_floor_and_diffuser_sync(self):
        self.mutated(lambda p:p['shops'][3]['fixtures'][0].update(color=[1,.2,.8]))
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(color=[1,1,1]))
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(fixtureIds=['S08_F01']))

    def test_protected_materials_and_groups_cannot_be_bound(self):
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(group='Infrastructure/Pole'))
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(sourceMaterial='Food'))
        self.mutated(lambda p:p['shops'][0]['emitters'][0].update(material='Food_Paper'))
        self.mutated(lambda p:p['shops'][0]['emitters'].append(copy.deepcopy(p['shops'][0]['emitters'][0])))

    def test_real_authored_geometry_preserved_exactly(self):
        for sid, (original, result) in self.venues.items():
            with self.subTest(venue=sid):
                g = copy.deepcopy(original); before_keys=list(g.batches); before_mats=copy.deepcopy(g.materials)
                before_arrays={key:copy.deepcopy(value) for key,value in g.batches.items()}
                state=np.random.get_state(); py_state=random.getstate()
                modified=vl.apply_shop(g,sid,result,self.profile,set(g.batches))
                self.assertEqual(random.getstate(),py_state)
                after_state=np.random.get_state()
                self.assertEqual(state[0],after_state[0]);np.testing.assert_array_equal(state[1],after_state[1]);self.assertEqual(state[2:],after_state[2:])
                bindings=next(s for s in self.profile['shops'] if s['id']==sid)['emitters']
                mapping={(b['group'],b['sourceMaterial']):(b['group'],b['material']) for b in bindings}
                self.assertEqual(list(g.batches),[mapping.get(k,k) for k in before_keys])
                self.assertEqual(len(g.batches),len(before_keys))
                for key, value in before_arrays.items():
                    actual=g.batches[mapping.get(key,key)]
                    self.assertEqual(set(actual),set(value))
                    for attr in ('v','f','uv'):np.testing.assert_array_equal(actual[attr],value[attr])
                    if 'authored_tints' in value:
                        for a,b in zip(actual['authored_tints'],value['authored_tints']):
                            self.assertEqual(a[:2],b[:2]);np.testing.assert_array_equal(a[2],b[2])
                for name, material in before_mats.items():self.assertEqual(g.materials[name],material)
                self.assertEqual(len(g.materials)-len(before_mats),len(bindings))
                for a,b in zip(result['lights'],modified['lights']):
                    self.assertEqual(a,{k:v for k,v in b.items() if k!='venueLighting'})
                for field in result:
                    if field!='lights':self.assertEqual(result[field],modified[field])

    def test_missing_binding_fails_before_any_mutation(self):
        g,result=copy.deepcopy(self.venues['S01']); before=copy.deepcopy(g.materials);keys=list(g.batches)
        key=(self.profile['shops'][0]['emitters'][0]['group'],'Food_Paper')
        with self.assertRaises(ValueError):vl.apply_shop(g,'S01',result,self.profile,set(g.batches)-{key})
        self.assertEqual(g.materials,before);self.assertEqual(list(g.batches),keys)

    def test_authored_fixture_drift_fails_before_any_mutation(self):
        for field, value in [('position',[0,0,0]),('range',6),('strength',2),('color',[1,1,1])]:
            g,result=copy.deepcopy(self.venues['S01']);result['lights'][0][field]=value
            before=copy.deepcopy(g.materials);keys=list(g.batches)
            with self.assertRaises(ValueError):vl.apply_shop(g,'S01',result,self.profile,set(g.batches))
            self.assertEqual(g.materials,before);self.assertEqual(list(g.batches),keys)

    def test_no_coordinate_heuristic_in_adapter(self):
        text=Path(vl.__file__).read_text()
        self.assertNotIn('argmin',text);self.assertNotIn('nearest',text.replace('No nearest-light','No local-light'))
        self.assertNotIn('np.random',text);self.assertNotIn('random.',text)
        self.assertIn('mapping.get(key, key)',text)

    def test_exact_preview_fallback_and_authored_mapping(self):
        base=dict(position=[1,2,3],range=4,strength=1.4)
        self.assertEqual(vl.preview_light(base),([1,.48,.16],154.))
        for shop in self.profile['shops']:
            for fixture in shop['fixtures']:
                spec=dict(strength=fixture['strength'],venueLighting=vl.light_metadata(shop,fixture))
                color,energy=vl.preview_light(spec)
                self.assertEqual(color,fixture['color'])
                self.assertEqual(energy,fixture['strength']*110*fixture['intensityMultiplier'])

    def test_clone_shader_routing_static_and_legacy_untouched(self):
        fantasy=json.loads((ROOT/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text())
        before=copy.deepcopy(fantasy)
        extended=vl.extend_fantasy_profile(fantasy,self.profile)
        self.assertEqual(fantasy,before)
        self.assertEqual(extended['materialGroups'][:len(before['materialGroups'])],before['materialGroups'])
        for group in extended['materialGroups'][len(before['materialGroups']):]:
            self.assertEqual(group['shader'],'LanternPaper')
            self.assertEqual(next(f['value'] for f in group['floats'] if f['name']=='_Breath'),0)

    def test_source_unity_baked_policy_and_preflight(self):
        builder=(ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
        runtime=(ROOT/'Assets/TreeTopYokocho/Editor/VenueLightingProfile.cs').read_text()
        pre=builder.index('VenueLightingProfile.Load(Root, manifest)')
        self.assertLess(pre,builder.index('Directory.CreateDirectory(Root + "/Generated")'))
        loop=builder[builder.index('for (int i = 0; i < manifest.lights.Length; i++)'):builder.index('var settings = new LightingSettings')]
        self.assertIn('l.lightmapBakeType = LightmapBakeType.Baked',loop)
        self.assertIn('l.shadows = LightShadows.Soft',loop)
        self.assertIn('l.range = spec.range * 1.25f',loop)
        self.assertIn('l.bounceIntensity = 1.6f',loop)
        self.assertIn('new Color(1, .52f, .18f)',runtime)
        self.assertIn('spec.strength * 1.65f',runtime)
        self.assertIn('material.SetFloat("_Breath", 0)',runtime)
        self.assertNotIn('Time.',runtime);self.assertNotIn('LightType.',runtime)

if __name__=='__main__':unittest.main()
