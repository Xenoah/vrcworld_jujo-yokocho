"""Actual native material usage, not inference from unused material definitions."""
import json,os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path(os.environ.get('YOKOCHO_ASSET_ROOT',ROOT))

def counts(path):
    result={}
    with path.open('rb') as f:
        if f.read(4)!=b'JYWM':raise ValueError('Wrong native visual signature')
        version,total=struct.unpack('<II',f.read(8))
        if version!=1:raise ValueError('Wrong native visual version')
        for _ in range(total):
            names=[]
            for _ in range(2):
                size,=struct.unpack('<I',f.read(4));names.append(f.read(size).decode())
            nv,ni=struct.unpack('<II',f.read(8));value=result.setdefault(names[1],[0,0]);value[0]+=1;value[1]+=ni//3
            f.seek(nv*24+ni*4,1)
        if f.read(1):raise ValueError('Trailing native bytes')
    return result
class ClothUse(unittest.TestCase):
    def test_profile_preserves_back_cull_for_authored_double_sided_mesh(self):
        p=json.loads((ROOT/'Assets/TreeTopYokocho/Data/FantasyMaterials.json').read_text())
        groups={n:g for g in p['materialGroups'] for n in g['names']}
        cull=lambda n:dict((x['name'],x['value']) for x in groups[n]['floats'])['_Cull']
        self.assertEqual(cull('ShopfrontTextile'),2)
        self.assertEqual(cull('CityWovenBanner'),0)
        for i in range(8):self.assertEqual(cull(f'Noren{i}'),2)
    def test_actual_current_cloth_roster(self):
        path=ASSETS/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'
        if not path.exists():self.skipTest('Set YOKOCHO_ASSET_ROOT to actual exported project for native-use evidence')
        use=counts(path);signs_active=False
        manifest=json.loads((ASSETS/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
        if manifest.get('features',{}).get('shop_personality') is True:
            sys.path.insert(0,str(ROOT/'Source'))
            import shop_personality_contract as shops
            ok,detail=shops.validate_native(ASSETS,manifest)
            self.assertTrue(ok,detail)
            if any(flag in manifest.get('features',{}) for flag in ('shop_rpg_identity','venue_lighting_identity')):
                # Actual current native/source admission above must succeed
                # before the exact accepted state's complete roster is used.
                import rpg_identity_contract as rpg
                import s05_pendant_contract as pendant
                import projecting_sign_contract as signs
                signs_active=signs.requested(manifest)
                accepted=(signs.load_oracle(ASSETS) if signs.requested(manifest) else pendant.load_oracle(ASSETS) if pendant.requested(manifest) else rpg.load_oracle(ASSETS)['variants'][rpg.variant_key(manifest)])
                expected_rows=accepted['rows']
            else:
                before=shops.load_before(ASSETS);oracle=shops.load_oracle(ASSETS)
                retired=set(map(tuple,before['shopKeys']))
                expected_rows=[r for r in before['rows'] if shops.key(r) not in retired]+oracle['shopRows']
            expected={}
            for row in expected_rows:
                value=expected.setdefault(row['material'],[0,0]);value[0]+=1;value[1]+=row['triangles']
            self.assertEqual(use,expected,'Actual native material use differs from exact new architecture roster')
            self.assertEqual(use.get('ShopfrontTextile',[0,0]),[0,0])
        else:
            self.assertEqual(use['ShopfrontTextile'],[8,27534])
        self.assertEqual(use['CityWovenBanner'],[1,15])
        for i in range(8):
            if signs_active and i in (1,3):
                # Only after actual frozen v2.19 admission above. Exactly these
                # immutable existing cloth definitions are newly activated.
                self.assertEqual(use.get(f'Noren{i}'),expected[f'Noren{i}'])
                self.assertEqual(use[f'Noren{i}'][0],1);self.assertGreater(use[f'Noren{i}'][1],0)
            else:self.assertEqual(use.get(f'Noren{i}',[0,0]),[0,0])
if __name__=='__main__':unittest.main()
