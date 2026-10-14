"""Portable food-v6 unit contracts. Run: python Source/test_food_venues.py

Reads only installed source plus testdata/shop_personality_before_2_15.json's
manifest. No Preview, Docs, sibling checkout, generated report or asset required.
Temporary atlas writes are private and cleaned up. Full-world access remains a
separate integration gate; these tests do not claim VRChat/runtime validation.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import random
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image
import food_venues as food
from world_geometry import Geometry

SOURCE = Path(__file__).resolve().parent
ROSTER = {0:(6.0,5.4,6), 1:(6.0,5.4,6), 2:(4.8,5.4,5),
          4:(7.2,6.0,8), 7:(6.0,5.4,6)}
M_KEYS = dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',
              wall='Plaster',tile='Kawara',window='WarmWindow',iron='Iron',
              ceramic='Ceramic',food='Food',red='RedLantern',city='TownLights',
              menu='MenuAtlas',tea='Tea',soy='Soy',noodle='Noodles',sweet='MatchaSweets')


def fingerprint(batches):
    digest=hashlib.sha256()
    for key,b in sorted(batches.items()):
        digest.update(json.dumps(key).encode())
        for field,dtype in [('v','<f8'),('f','<u4'),('uv','<f8')]:
            digest.update(np.asarray(b[field],dtype=dtype).tobytes())
    return digest.hexdigest()


def fixture(materials,idx,angle=0.0,offset=(0.,0.,0.)):
    g=Geometry()
    for item in materials:
        args=copy.deepcopy(item);name=args.pop('name');g.material(name,**args)
    original=copy.deepcopy(g.materials);M=dict(M_KEYS)
    for item in food.material_specs():
        args=copy.deepcopy(item);key=args.pop('key');name=args.pop('name')
        if key in M or name in g.materials:raise AssertionError('Material collision')
        M[key]=g.material(name,**args)
    g.group='UnitSentinel';g.box([29,37,43],[1,2,3],'Iron')
    sentinel=copy.deepcopy(g.batches[('UnitSentinel','Iron')])
    sid=f'S{idx+1:02d}';g.group='Shops/'+sid
    origin=np.asarray(offset,float)
    right=np.array([math.cos(angle),-math.sin(angle),0.])
    front=np.array([math.sin(angle),math.cos(angle),0.]);up=np.array([0.,0.,1.])
    axes=np.array([right,front,up]);solid_calls=[]
    def P(x,y,z):return origin+right*x+front*y+up*z
    def B(x,y,z,w,d,h,material,solid=False):
        if solid:solid_calls.append([x,y,z])
        g.box(P(x,y,z),(w,d,h),material,axes)
    w,d,count=ROSTER[idx];spread=min(w-1.5,(count-1)*.7)
    seats=[dict(id=f'{sid}_Seat_{j+1}',position=[-spread/2+spread*j/(count-1),d/2+.65,.70],
                exit=[-spread/2+spread*j/(count-1),d/2+1.35,.06],forward=[0,-1,0]) for j in range(count)]
    inputs=copy.deepcopy(seats)
    report=food.build_venue(g,P,B,w,d,idx,M,seat_specs=seats,lantern=None)
    return dict(g=g,report=report,original=original,sentinel=sentinel,seats=seats,
                inputs=inputs,solidCalls=solid_calls,axes=axes,origin=origin)


class FoodVenueUnits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deliberately do not consume layout or generated reports from this oracle.
        manifest=json.loads((SOURCE/'testdata/shop_personality_before_2_15.json').read_text())['manifest']
        cls.materials=manifest['materials']
        cls.np_state=np.random.get_state();cls.py_state=random.getstate()
        cls.base={i:fixture(cls.materials,i) for i in ROSTER}
        cls.repeat={i:fixture(cls.materials,i) for i in ROSTER}
        cls.transformed={i:fixture(cls.materials,i,.731,(13.1,-7.7,40.)) for i in ROSTER}
        cls.np_after=np.random.get_state();cls.py_after=random.getstate()

    def test_fixed_roster_and_material_namespace(self):
        self.assertEqual(tuple(ROSTER),tuple(food.SHOP_IDS))
        specs=food.material_specs();names=[s['name'] for s in specs];keys=[s['key'] for s in specs]
        self.assertEqual(len(names),len(set(names)));self.assertEqual(len(keys),len(set(keys)))
        self.assertTrue(all(n.startswith('Food_') for n in names))
        self.assertEqual(sum(len(f['report']['seatOverrides']) for f in self.base.values()),31)
        for idx,f in self.base.items():
            with self.subTest(shop=idx):
                r=f['report'];sid=f'S{idx+1:02d}'
                self.assertEqual(r['shop'],sid);self.assertIs(r['completeVisualReplacement'],True)
                self.assertEqual({s['id'] for s in r['seatOverrides']},{s['id'] for s in f['inputs']})
                self.assertEqual(len(r['seatOverrides']),ROSTER[idx][2])
                self.assertEqual(f['seats'],f['inputs'])
                self.assertEqual(len(r['solids']),len({s['name'] for s in r['solids']}))
                for solid in r['solids']:
                    self.assertTrue(np.isfinite(solid['center']).all());self.assertGreater(min(solid['size']),0)
                for seat in r['seatOverrides']:
                    self.assertTrue(np.isfinite(seat['position']+seat['exit']+seat['forward']).all())
                    self.assertAlmostEqual(np.linalg.norm(seat['forward']),1);self.assertEqual(seat['forward'][2],0)

    def test_ownership_and_no_implicit_physics(self):
        for idx,f in self.base.items():
            with self.subTest(shop=idx):
                g=f['g'];sid=f'S{idx+1:02d}'
                self.assertEqual(g.group,'Shops/'+sid);self.assertEqual(f['solidCalls'],[])
                self.assertEqual(g.batches[('UnitSentinel','Iron')],f['sentinel'])
                for name,descriptor in f['original'].items():self.assertEqual(g.materials[name],descriptor)
                for (group,material),batch in g.batches.items():
                    if group=='UnitSentinel':continue
                    self.assertTrue(group.startswith('Shops/'+sid+'/Personality/'))
                    self.assertIn(material,g.materials)
                    v=np.asarray(batch['v']);uv=np.asarray(batch['uv']);faces=np.asarray(batch['f'])
                    self.assertTrue(np.isfinite(v).all() and np.isfinite(uv).all())
                    self.assertEqual(len(v),len(uv));self.assertGreaterEqual(faces.min(),0);self.assertLess(faces.max(),len(v))

    def test_determinism_and_no_global_rng_mutation(self):
        for idx in ROSTER:
            with self.subTest(shop=idx):
                self.assertEqual(fingerprint(self.base[idx]['g'].batches),fingerprint(self.repeat[idx]['g'].batches))
                self.assertEqual(self.base[idx]['report'],self.repeat[idx]['report'])
        self.assertEqual(self.py_state,self.py_after)
        self.assertTrue(all(np.array_equal(a,b) for a,b in zip(self.np_state,self.np_after)))

    def test_transformed_frame_local_metadata_and_envelope(self):
        for idx,f in self.transformed.items():
            with self.subTest(shop=idx):
                self.assertEqual(f['report'],self.base[idx]['report'])
                self.assertEqual(f['g'].group,f'Shops/S{idx+1:02d}')
                vertices=np.concatenate([np.asarray(b['v']) for (group,_),b in f['g'].batches.items() if group!='UnitSentinel'])
                local=(vertices-f['origin'])@f['axes'].T
                w,d,_=ROSTER[idx]
                self.assertLessEqual(abs(local[:,0]).max(),w/2+.50)
                self.assertGreaterEqual(local[:,1].min(),-d/2-.50)
                self.assertLessEqual(local[:,1].max(),d/2+1.05)
                self.assertGreaterEqual(local[:,2].min(),-.02);self.assertLessEqual(local[:,2].max(),4.3)

    def test_explicit_service_routes_and_bounded_effects(self):
        for idx,f in self.base.items():
            with self.subTest(shop=idx):
                r=f['report'];roles={p['role'] for p in r['routes']}
                self.assertTrue({'entrance','staff'}.issubset(roles))
                for route in r['routes']:
                    self.assertGreaterEqual(len(route['points']),2)
                    self.assertTrue(all(len(p)==3 and np.isfinite(p).all() for p in route['points']))
                    if route['role'] in ('entrance','staff'):
                        self.assertGreaterEqual(route['radius'],.325);self.assertGreaterEqual(route['headroom'],2.2)
                self.assertLessEqual(len(r['lights']),2);self.assertLessEqual(sum(l['strength'] for l in r['lights']),3)
                self.assertLessEqual(len(r['steam']),1)
                if idx in (4,7):self.assertEqual(r['steam'],[])

    def test_baked_atlas_portable_fallback(self):
        original_exists=Path.exists
        def without_fonts(path):
            return False if path.suffix.lower() in ('.ttf','.ttc','.otf') else original_exists(path)
        with tempfile.TemporaryDirectory(prefix='food-atlas-unit-') as temporary:
            p=Path(temporary)/food.ATLAS_NAME;Image.new('RGB',(2048,2048),(211,191,155)).save(p)
            # A cached atlas may now be RPG output. Offline legacy fallback
            # must restore the immutable v2.16 original, not trust stale pixels.
            baseline=SOURCE/'testdata/rpg_signs_baseline'/food.ATLAS_NAME
            expected=baseline.read_bytes()
            with mock.patch.object(Path,'exists',without_fonts):result=food.bake_textures(temporary)
            self.assertEqual(p.read_bytes(),expected);self.assertEqual(result['width'],2048)
            self.assertEqual(result['height'],2048);self.assertEqual(result['bytes'],len(expected))
            self.assertEqual(result['source'],'pinned-original-v2.16-atlas')
            self.assertEqual([q.name for q in Path(temporary).iterdir()],[food.ATLAS_NAME])

    def test_fresh_atlas_deterministic_when_authoring_font_available(self):
        fonts=[SOURCE/'NotoSansCJKjp-Regular.otf',Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')]
        font=next((p for p in fonts if p.exists()),None)
        if font is None:self.skipTest('No Japanese authoring font; portable baked-atlas fallback tested separately')
        with tempfile.TemporaryDirectory(prefix='food-atlas-unit-') as temporary:
            a=food.bake_textures(temporary,font);p=Path(temporary)/food.ATLAS_NAME;first=p.read_bytes()
            b=food.bake_textures(temporary,font)
            self.assertEqual(a,b);self.assertEqual(first,p.read_bytes())
            self.assertEqual([q.name for q in Path(temporary).iterdir()],[food.ATLAS_NAME])
            with Image.open(p) as image:
                self.assertEqual(image.size,(2048,2048));self.assertEqual(image.mode,'RGB')
                self.assertGreater(np.asarray(image).std(),10)


if __name__=='__main__':unittest.main(verbosity=2)
