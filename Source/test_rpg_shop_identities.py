"""Identity-only contracts; never a Unity/VRChat runtime certification."""
from pathlib import Path
from functools import partial
import copy,hashlib,json,pickle,tempfile,unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from fontTools.ttLib import TTFont
import rpg_shop_identities as rpg
import food_venues as food
import nightlife_venues as night
import test_food_venues as food_fixture
import test_nightlife_venues as night_fixture

SOURCE=Path(__file__).resolve().parent

def make(idx,enabled):
    if idx in rpg.FOOD_IDS:
        materials=json.loads((SOURCE/'testdata/shop_personality_before_2_15.json').read_text())['manifest']['materials']
        original=food.build_venue
        with patch.object(food,'build_venue',partial(original,rpg_identity=enabled)):
            f=food_fixture.fixture(materials,idx)
        return f['g'],f['report']
    original=night_fixture.build_venue
    with patch.object(night_fixture,'build_venue',partial(original,rpg_identity=enabled)):
        return night_fixture.make(idx)

class IdentityTests(unittest.TestCase):
    def test_literal_booleans(self):
        for m in [food,night]:
            for v in [1,0,None,'true',[]]:
                with self.assertRaises(ValueError):m.bake_textures('/tmp/must-not-write-rpg',rpg_identity=v)
                with self.assertRaises(ValueError):m.build_venue(None,None,None,None,None,None,None,seat_specs=[],rpg_identity=v)
    def test_bundled_glyphs_hashes_and_licenses(self):
        mf=rpg._font_manifest()
        for face,spec in mf['faces'].items():
            p=rpg.FONT_DIR/spec['file'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),spec['sha256'])
            f=TTFont(p);cmap=f.getBestCmap();self.assertEqual(sorted(cmap),spec['codepoints'])
            for i,item in rpg.IDENTITIES.items():
                if item['face']==face:
                    for ch in item['name']:
                        self.assertIn(ord(ch),cmap);self.assertNotEqual(cmap[ord(ch)],'.notdef')
            self.assertTrue(any(n.toUnicode().startswith('Yokocho') for n in f['name'].names if n.nameID==1))
        for rel in ['OFL.txt','upstream/kleeone/OFL.txt','upstream/kaiseidecol/OFL.txt']:
            text=(rpg.FONT_DIR/rel).read_text();self.assertIn('SIL OPEN FONT LICENSE Version 1.1',text);self.assertIn('Copyright' if rel!='OFL.txt' else 'Adobe',text)
    def test_main_ink_margins_and_glyph_aspect(self):
        for idx,item in rpg.IDENTITIES.items():
            r=rpg.name_rect(idx);w,h=r[2]-r[0],r[3]-r[1]
            self.assertLess(abs((w/h)/rpg.ASPECTS[idx]-1),.004)
            _,info=rpg._sign(idx,(w,h));a,b,c,d=info['inkBounds']
            self.assertEqual(info['text'],item['name']);self.assertGreater(a,h*.9);self.assertLess(c,w-h*.25)
            self.assertGreater(b,h*.15);self.assertLess(d,h*.88)
    def test_pixel_scope_repeat_and_transition(self):
        for module,atlas in [(food,food.ATLAS_NAME),(night,night.ATLAS)]:
            with tempfile.TemporaryDirectory() as td:
                report=module.bake_textures(td,rpg_identity=True);p=Path(td)/atlas;raw=p.read_bytes();im=np.array(Image.open(p))
                base=np.array(Image.open(SOURCE/'testdata/rpg_signs_baseline'/atlas));mask=np.zeros((2048,2048),bool)
                for x0,y0,x1,y1 in rpg.owned_rectangles(atlas):mask[y0:y1,x0:x1]=True
                np.testing.assert_array_equal(im[~mask],base[~mask]);self.assertTrue(np.any(im[mask]!=base[mask]))
                self.assertEqual(report,module.bake_textures(td,rpg_identity=True));self.assertEqual(raw,p.read_bytes())
                # No system font available: disabled must restore original, not stale RPG.
                exists=Path.exists
                with patch.object(Path,'exists',lambda q:False if q.suffix in ('.ttf','.ttc','.otf') else exists(q)):
                    module.bake_textures(td,rpg_identity=False)
                self.assertEqual(p.read_bytes(),(SOURCE/'testdata/rpg_signs_baseline'/atlas).read_bytes())
                module.bake_textures(td,rpg_identity=True);self.assertEqual(raw,p.read_bytes())
    def test_geometry_and_metadata_change_only_permitted_sign_uvs(self):
        changes=[]
        for idx in range(8):
            old,a=make(idx,False);new,b=make(idx,True)
            self.assertEqual(list(old.batches),list(new.batches));self.assertEqual(old.materials,new.materials)
            self.assertEqual(b.pop('displayName'),rpg.IDENTITIES[idx]['name'])
            if idx in rpg.NIGHT_IDS:self.assertEqual(b.pop('name'),rpg.IDENTITIES[idx]['name']);a.pop('name')
            self.assertEqual(a,b)
            changed=[]
            for key in old.batches:
                x,y=old.batches[key],new.batches[key]
                for field in x:
                    if field!='uv':self.assertEqual(pickle.dumps(x[field],protocol=4),pickle.dumps(y[field],protocol=4))
                if not np.array_equal(x['uv'],y['uv']):
                    self.assertIn(key[1],('Food_Sign','Night_Print'))
                    self.assertTrue('Signs' in key[0] or 'Signage' in key[0]);changed.append(key)
            self.assertTrue(changed);changes+=changed
        self.assertEqual(len(changes),8)
    def test_night_portrait_and_crest_aspects(self):
        for slot,size in [(1,(.32,.69)),(2,(.30,.30))]:
            a,b,c,d=rpg.night_rect(slot,size);self.assertLess(abs(((c-a)/(d-b))/(size[0]/size[1])-1),.004)
    def test_missing_or_corrupt_font_fails_instead_of_tofu(self):
        spec=copy.deepcopy(rpg._font_manifest());spec['faces']['Serif-Bold']['sha256']='0'*64
        rpg.font.cache_clear()
        with patch.object(rpg,'_font_manifest',return_value=spec):
            with self.assertRaises(ValueError):rpg.font('Serif-Bold',31)
        rpg.font.cache_clear()

if __name__=='__main__':unittest.main(verbosity=2)
