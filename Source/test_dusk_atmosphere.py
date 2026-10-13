"""Deterministic source-math/contract checks. These are NOT Unity compilation.
Run: python Source/test_dusk_atmosphere.py [--report path.json]
"""
import argparse, copy, hashlib, json, math, random, re, sys, unittest
from pathlib import Path
from dusk_atmosphere import load_profile, source_to_unity, sky_radiance, fog_transmission, fbm, profile_digest, PROFILE_RELATIVE
ROOT=Path(__file__).resolve().parent.parent
PROFILE=load_profile(ROOT/PROFILE_RELATIVE)

class DuskContracts(unittest.TestCase):
    def test_direction_conversion_and_roundtrip(self):
        self.assertEqual(source_to_unity((2,3,5)),(2,5,3))
        self.assertEqual(source_to_unity(source_to_unity((2,3,5))),(2,3,5))
        self.assertEqual(source_to_unity(PROFILE['sky']['sunsetDirection']),(-.8,0.,.6))
        d=PROFILE['fill']['towardLight'];s=PROFILE['sky']['sunsetDirection']
        self.assertAlmostEqual(d[0]/d[1],s[0]/s[1],places=5)
    def test_sky_altitude_is_nonflat(self):
        colors=[sky_radiance((0,math.cos(math.radians(a)),math.sin(math.radians(a))),PROFILE) for a in (0,30,60)]
        luminance=[sum(c*w for c,w in zip(rgb,(.2126,.7152,.0722))) for rgb in colors]
        self.assertGreater(luminance[0],luminance[1]);self.assertGreater(luminance[1],luminance[2])
        self.assertGreater(luminance[0]-luminance[2],.10)
    def test_warmth_is_directional_and_horizon_bound(self):
        warm=sky_radiance((-.8,.6,.035),PROFILE);cold=sky_radiance((.8,-.6,.035),PROFILE)
        self.assertGreater(warm[0]/warm[2],cold[0]/cold[2]*1.7)
        high=sky_radiance((-.4,.3,.8660254),PROFILE)
        self.assertLess(high[0],warm[0]*.2)
    def test_noise_stable_and_no_random_state_changes(self):
        before=random.getstate();coords=[(-3.5,4.8),(0,0),(13.2,-5.7),(88.1,7.2)]
        first=[fbm(*p) for p in coords];second=[fbm(*p) for p in coords]
        self.assertEqual(first,second);self.assertEqual(before,random.getstate())
        self.assertTrue(all(0<=v<=.96875 for v in first));self.assertGreater(max(first)-min(first),.10)
        self.assertEqual(profile_digest(PROFILE),profile_digest(copy.deepcopy(PROFILE)))
    def test_exp2_depth_at_both_candidates(self):
        for density in (.00028,.00040):
            values=[fog_transmission(d,density) for d in (0,50,740,1500,2500)]
            self.assertEqual(values[0],1.);self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
            self.assertGreater(values[1],.9995)
        self.assertAlmostEqual(fog_transmission(2500,.0004),math.exp(-1),places=12)
        self.assertAlmostEqual(fog_transmission(1500,.0004),.697676326071031,places=12)
        self.assertEqual(fog_transmission(-100,.0004),1.)
    def test_sky_shader_keeps_resource_mechanism(self):
        source=(ROOT/'Assets/TreeTopYokocho/Shaders/YokochoSky.shader').read_text()
        self.assertEqual(len(re.findall(r'^\s*Pass\s*$',source,re.M)),1)
        self.assertIn('for(int i=0;i<5;i++)',source)
        for forbidden in ('sampler2D','sampler3D','samplerCUBE','tex2D','GrabPass','_Time'):
            self.assertNotIn(forbidden,source)
        self.assertIn('normalize(_SunsetDirection.xz)',source)
        self.assertIn('UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX',source)
        self.assertIn('UNITY_VERTEX_OUTPUT_STEREO',source)
    def test_profile_consumed_and_fixed_exposure(self):
        builder=(ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
        preview=(ROOT/'Source/render_preview.py').read_text()
        for field in ('ambient.sky','ambient.equator','ambient.ground','fog.density','fog.color','display.unityPostExposure'):
            self.assertIn('atmosphere.'+field,builder)
        self.assertIn("scene.view_settings.exposure=atmosphere['display']['blenderExposure']",preview)
        self.assertNotIn('ShaderNodeVolumeScatter',preview);self.assertNotIn('primitive_cube_add',preview)
        for key in ('atmosphere_profile_sha256','atmosphere_effective_sha256','render_script_sha256','atmosphere_script_sha256'):
            self.assertIn("'"+key+"'",preview)
        self.assertIn("configure_surface_fog(bpy,atmosphere)",preview)
        self.assertEqual(PROFILE['display']['blenderExposure'],.2)
        self.assertEqual(PROFILE['display']['unityPostExposure'],.25)
    def test_explicit_color_encoding(self):
        shader=(ROOT/'Assets/TreeTopYokocho/Shaders/YokochoSky.shader').read_text()
        helper=(ROOT/'Assets/TreeTopYokocho/Editor/DuskAtmosphereProfile.cs').read_text()
        builder=(ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs').read_text()
        for name in ('_Horizon','_Zenith','_SunsetColor','_HighCloudTint'):
            self.assertRegex(shader,re.escape(name)+r'\([^\n]*,Vector\)')
            self.assertIn('material.SetVector("'+name+'", LinearRGB(',helper)
        self.assertIn('RGB(atmosphere.fog.color).gamma',builder)
        self.assertNotIn('lightsUseLinearIntensity =',builder)
    def test_fog_cannot_become_a_sampled_mesh_light(self):
        module=(ROOT/'Source/dusk_atmosphere.py').read_text()
        preview=(ROOT/'Source/render_preview.py').read_text()
        self.assertIn("mat.cycles.emission_sampling='NONE'",module)
        self.assertIn("l.new(camera_ray.outputs['Is Camera Ray'],emission.inputs['Strength'])",module)
        self.assertLess(preview.index("# Only camera-visible lantern emission"),preview.index("configure_surface_fog(bpy,atmosphere)"))
    def test_no_runtime_components_or_rng_added(self):
        helper=(ROOT/'Assets/TreeTopYokocho/Editor/DuskAtmosphereProfile.cs').read_text()
        self.assertTrue(helper.startswith('#if UNITY_EDITOR && !COMPILER_UDONSHARP'))
        for word in ('AddComponent','new GameObject','UnityEngine.Random','Resources.Load','UdonBehaviour','Texture2D'):
            self.assertNotIn(word,helper)
        module=(ROOT/'Source/dusk_atmosphere.py').read_text()
        for word in ('import random','import numpy','primitive_','bpy.data.lights.new','bpy.data.images.new'):
            self.assertNotIn(word,module)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DuskContracts))
    if args.report:
        args.report.write_text(json.dumps({'scope':'Deterministic source math and source contracts; not Unity compilation, bake, runtime or performance verification','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'profile_sha256':hashlib.sha256((ROOT/PROFILE_RELATIVE).read_bytes()).hexdigest(),'effective_profile_sha256':profile_digest(PROFILE),'fog':{str(density):{str(d):fog_transmission(d,density) for d in (0,50,740,1500,2500)} for density in (.00028,.0004)}},indent=2))
    sys.exit(not result.wasSuccessful())
