"""Source/numeric guards, NOT a substitute for Unity shader compilation."""
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHADERS = ROOT / 'Assets/TreeTopYokocho/Shaders'
PROFILE = ROOT / 'Assets/TreeTopYokocho/Data/FantasyMaterials.json'

class FantasyShaderContract(unittest.TestCase):
    def test_no_extra_scene_passes_or_screen_sampling(self):
        for file in SHADERS.glob('*.shader'):
            text = file.read_text()
            self.assertEqual(text.count('{'), text.count('}'), file.name)
            self.assertNotIn('GrabPass {', text)
            self.assertNotIn('_CameraDepthTexture', text)
        for name in ('Cloth','LanternPaper','Water','Surface','Glaze'):
            s=(SHADERS/f'Yokocho{name}.shader').read_text()
            self.assertIn('"RenderType"="Opaque"',s)
            self.assertNotIn('Blend ',s)
            self.assertIn('#pragma multi_compile_instancing',s)
            self.assertIn('addshadow',s)

    def test_scene_identity_and_unique_material_routing(self):
        p=json.loads(PROFILE.read_text()); names=[]
        for group in p['materialGroups']:
            names.extend(group['names'])
            shader=(SHADERS/f'Yokocho{group["shader"]}.shader').read_text()
            for prop in group.get('floats',[]):
                self.assertIn(prop['name'],shader)
            for kw in group.get('keywords',[]):
                self.assertIn('#pragma shader_feature_local '+kw,shader)
        self.assertEqual(len(names),len(set(names)))
        self.assertNotIn('SignAtlas',names)
        self.assertNotIn('MenuAtlas',names)
        self.assertNotIn('AviationRed',names)

    def test_water_planar_optimization_and_normal_frame(self):
        s=(SHADERS/'YokochoWater.shader').read_text()
        self.assertNotRegex(s,r'\bvertex\s*:')
        self.assertNotRegex(s,r'\.vertex\s*[+*/-]?=')
        self.assertIn('YOKOCHO_STATIC_PLANAR_SEA',s)
        self.assertNotIn('v.vertex',s)
        self.assertIn('IN.worldPos.xz',s)
        self.assertEqual(s.count('WorldNormalVector(IN,'),3)
        self.assertIn('fwidth(phase)',s)
        # Worst-case analytic slope and texture ripple remains upward-facing.
        for a in range(0,360,7):
            x=math.cos(math.radians(a))*.018+.24
            z=math.sin(math.radians(a))*.018+.24
            y=1/math.sqrt(1+x*x+z*z)
            self.assertGreater(y,.93)

    def test_lantern_slow_bounded_and_static_bake(self):
        s=(SHADERS/'YokochoLanternPaper.shader').read_text()
        self.assertIn('#if !defined(UNITY_PASS_META)',s)
        self.assertIn('clamp(_Breath,0,.03)',s)
        self.assertIn('sin(_Time.y*.31)',s)
        # Not a blink: full period >20s, luminance never reaches zero.
        self.assertGreater(2*math.pi/.31,20)
        self.assertGreater(1-.03,.95)

    def test_cloth_filter_and_non_emissive_sheen(self):
        s=(SHADERS/'YokochoCloth.shader').read_text()
        self.assertIn('fwidth(thread.x)',s)
        self.assertIn('float facing:VFACE',s)
        self.assertIn('o.Emission = 0',s)
        self.assertIn('StandardSpecular',s)
        self.assertIn('#if !defined(UNITY_PASS_META)',s)
        self.assertIn('* IN.color.rgb',s)
        self.assertNotIn('vertex:vert',s)

    def test_glaze_energy_and_no_animation(self):
        s=(SHADERS/'YokochoGlaze.shader').read_text()
        self.assertNotIn('_Time',s)
        self.assertIn('o.Emission=0',s)
        self.assertIn('#if !defined(UNITY_PASS_META)',s)
        self.assertIn('color*(1-metal)',s)
        # For every allowed input, film multiplier remains in [0.9,1.1].
        for angle in range(101):
            grazing=(angle/100)**2
            for channel in (0,2.0943951,4.1887902):
                film=.5+.5*math.cos(angle/100*2*math.pi+channel)
                factor=1+((.6+.8*film)-1)*.25*grazing
                self.assertGreaterEqual(factor,.9)
                self.assertLessEqual(factor,1.1)

    def test_sky_stereo_and_low_tier(self):
        s=(SHADERS/'YokochoSky.shader').read_text()
        self.assertIn('UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX',s)
        self.assertIn('UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO',s)
        self.assertIn('#if defined(_YOKOCHO_FANTASY_SKY)',s)
        stars=s.split('float stars(float3 d)')[1].split('float aurora')[0]
        self.assertNotIn('_Time',stars)
        self.assertIn('ddx(grid)',stars)
        self.assertIn('floor(cell.x/256.0)*256.0',stars)
        self.assertIn('min(width,.18)',stars)
        self.assertLess(.065+.18,.25)
        self.assertIn('(1-smoothstep(.80,.98,d.y))',stars)
        self.assertIn('float4 frag',s)

if __name__=='__main__': unittest.main()
