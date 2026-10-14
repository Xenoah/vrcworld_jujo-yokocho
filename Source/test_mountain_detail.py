"""Portable exact 12-batch adaptive-mountain geometry and gate regression."""
import ast,copy,hashlib,json,random,sys,unittest
from pathlib import Path
import numpy as np
from world_geometry import Geometry
from fantasy_landscape import _mountains,_mountain_height,apply_snow_deposition
from test_snow_deposition import geometry,ORIGINAL_AST
from mountain_detail import apply_mountain_detail,KEYS,adaptive_surface
import mountain_detail_contract as contract
from mountain_detail_test_fixture import frozen_arrays,restore_prior_mountains
from peer_culling_contract import summarize,raw_attributes,read_visual
ROOT=Path(__file__).resolve().parents[1]


def build(detail,snow):
    g=geometry()
    if detail is True:apply_mountain_detail(g)
    if snow is True:apply_snow_deposition(g)
    g.compact();g.bake_mood([])
    return g


def native(g):
    return [dict(group=k[0],material=k[1],vertices=b['v'],uv=b['uv'],faces=b['f'],colors=(b['colors']*255).astype('u1')) for k,b in g.batches.items()]


class MountainDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.variants={(d,s):native(build(d,s)) for d in (False,True) for s in (False,True)}
        cls.after=cls.variants[True,True];cls.before=cls.variants[False,True]

    def test_exact_four_frozen_variants_and_twelve_changed_records(self):
        for (detail,snow),batches in self.variants.items():
            features={'mountain_detail':detail,'snow_deposition':snow}
            self.assertTrue(contract.validate_native_mountains(batches,features)['passed'])
            frozen=frozen_arrays(('after' if detail else 'before')+('_snow' if snow else '_plain'))
            self.assertEqual([raw_attributes(b) for b in batches],[raw_attributes(b) for b in frozen])
        self.assertEqual([k for k,a,b in zip(KEYS,self.before,self.after) if raw_attributes(a)!=raw_attributes(b)],list(KEYS))
        self.assertEqual(sum(len(b['faces']) for b in self.after),15256)
        self.assertEqual(sum(len(b['vertices']) for b in self.after),9690)
        self.assertLessEqual(sum(len(b['faces']) for b in self.after)-sum(len(b['faces']) for b in self.before),5000)

    def test_gate_is_literal_and_wrong_side_payload_fails(self):
        for snow in (False,True):
            for detail in (False,True):
                bad=contract.validate_native_mountains(self.variants[not detail,snow],{'mountain_detail':detail,'snow_deposition':snow})
                self.assertFalse(bad['passed'])
        for value in ('true',1,None,[]):
            with self.assertRaises(ValueError):contract.expected_records({'mountain_detail':value})
        self.assertEqual(contract.expected_records({}),contract.expected_records({'mountain_detail':False,'snow_deposition':False}))

    def test_native_mutations_and_extra_identity_are_rejected(self):
        features={'mountain_detail':True,'snow_deposition':True}
        for field in ('vertices','uv','colors','faces'):
            batches=copy.deepcopy(self.after)
            if field=='faces':batches[0][field][0]=batches[0][field][0,::-1]
            elif field=='colors':batches[0][field].flat[0]^=1
            else:batches[0][field].flat[0]+=1
            self.assertFalse(contract.validate_native_mountains(batches,features)['passed'],field)
        self.assertFalse(contract.validate_native_mountains(self.after[:-1],features)['passed'])
        self.assertFalse(contract.validate_native_mountains(self.after+[self.after[0]],features)['passed'])
        b=copy.deepcopy(self.after[0]);b['group']='Landscape/SnowRange_4'
        self.assertFalse(contract.validate_native_mountains(self.after+[b],features)['passed'])

    def test_legacy_functions_are_unchanged(self):
        tree=ast.parse((ROOT/'Source/fantasy_landscape.py').read_text());func={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
        for name,pin in ORIGINAL_AST.items():self.assertEqual(hashlib.sha256(ast.dump(func[name],include_attributes=False).encode()).hexdigest(),pin)

    def test_unrelated_payload_materials_and_rng_unchanged(self):
        g=geometry();g.group='Unrelated/Sentinel';g.material('Sentinel',(.1,.2,.3));g.add([(1,2,3),(4,5,6),(7,8,10)],[(0,1,2)],'Sentinel')
        before=copy.deepcopy(g.batches[('Unrelated/Sentinel','Sentinel')]);materials=copy.deepcopy(g.materials);rng=random.getstate();nr=np.random.get_state();group=g.group
        apply_mountain_detail(g)
        self.assertEqual(before,g.batches[('Unrelated/Sentinel','Sentinel')]);self.assertEqual(materials,g.materials);self.assertEqual(group,g.group)
        self.assertEqual(rng,random.getstate());new=np.random.get_state();np.testing.assert_array_equal(nr[1],new[1]);self.assertEqual(nr[0],new[0]);self.assertEqual(nr[2:],new[2:])

    def test_unexpected_source_and_wrong_order_rejected_atomically(self):
        for mutation in ('vertex','face','uv','tint','missing'):
            g=geometry()
            if mutation=='vertex':g.batches[KEYS[0]]['v'][0][2]+=.01
            if mutation=='uv':g.batches[KEYS[0]]['uv'][0][0]+=.01
            if mutation=='face':g.batches[KEYS[0]]['f'][0].reverse()
            if mutation=='tint':apply_snow_deposition(g)
            if mutation=='missing':del g.batches[KEYS[0]]
            before=copy.deepcopy(g.batches)
            with self.assertRaises(ValueError):apply_mountain_detail(g)
            self.assertEqual(repr(before),repr(g.batches))

    def test_conforming_surface_across_sector_and_material_boundaries(self):
        allv=np.concatenate([b['vertices'] for b in self.after]);faces=[];offset=0
        for b in self.after:faces.extend(b['faces']+offset);offset+=len(b['vertices'])
        # Float32 native vertices pack coordinates identically on every seam.
        vv,index,inverse=np.unique(allv,axis=0,return_index=True,return_inverse=True);f=inverse[np.asarray(faces)]
        self.assertEqual(len(np.unique(np.sort(f,axis=1),axis=0)),len(f))
        edge=np.sort(np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1);edges,counts=np.unique(edge,axis=0,return_counts=True)
        self.assertTrue(np.all((counts==1)|(counts==2)))
        boundary=vv[edges[counts==1]]
        on_domain=np.any(np.stack([np.all(boundary[:,:,0]==x,axis=1) for x in (-3000,3000)]+[np.all(boundary[:,:,1]==y,axis=1) for y in (1240,3860)]),axis=0)
        self.assertTrue(np.all(on_domain),int((~on_domain).sum()))

    def test_exact_xy_domain_old_boundary_samples_and_projected_uv(self):
        allv=np.concatenate([b['vertices'] for b in self.after]);before=np.concatenate([b['vertices'] for b in self.before]);coords={tuple(p) for p in allv}
        np.testing.assert_array_equal(allv[:,:2].min(0),[-3000,1240]);np.testing.assert_array_equal(allv[:,:2].max(0),[3000,3860])
        # All old unclipped grid samples at external/sector boundaries remain.
        for x in np.linspace(-3000,3000,105):
            for y in (1240.,3860.):self.assertIn(tuple(np.asarray((x,y,_mountain_height(x,y)),np.float32)),coords)
        for x in (-3000.,-1500.,0.,1500.,3000.):
            for y in np.linspace(1240,3860,50):self.assertIn(tuple(np.asarray((x,y,_mountain_height(x,y)),np.float32)),coords)
        for b in self.after:
            self.assertLess(float(np.max(np.abs(b['uv'].astype(float)-b['vertices'][:,:2].astype(float)*.012))),5e-6)
            self.assertTrue(np.isfinite(b['vertices']).all());q=b['vertices'][b['faces']].astype(float);area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
            self.assertTrue(np.all(area>1e-6));self.assertEqual(len(np.unique(b['faces'])),len(b['vertices']))

    def test_snow_rgba_and_shared_material_seam_coverage(self):
        bypos={}
        bases={'AlpineSnow':np.array((.88,.93,.97)),'AlpineSnowShade':np.array((.60,.72,.82))};rock=np.array((.025,.028,.0055))
        # Reconstruct deposition coverage from Color32 red. Quantization limits
        # coverage precision; compare to the worst-case single-step bound.
        for b in self.after:
            self.assertTrue(np.all(b['colors'][:,3]==255))
            if b['material'] not in bases:continue
            base=bases[b['material']];ratio=rock/base
            coverage=(b['colors'][:,:3]/255.-ratio)/(.95-ratio)
            for p,c in zip(b['vertices'],coverage):bypos.setdefault(tuple(p),[]).append(c)
        shared=0
        for values in bypos.values():
            if len(values)>1:
                shared+=1;self.assertLess(float(np.max(np.ptp(values,axis=0))),.0048)
        self.assertGreater(shared,100)

    def test_exact_expectation_composition_and_test_only_inverse(self):
        for snow in (False,True):
            before=contract.expected_records({'snow_deposition':snow});before[('Unrelated','M')]={'sentinel':True}
            after=contract.compose_expected_records(before,{'snow_deposition':snow,'mountain_detail':True})
            self.assertEqual(after[('Unrelated','M')],before[('Unrelated','M')]);self.assertEqual(set(after),set(before))
            bad=copy.deepcopy(before);bad[KEYS[0]]['triangles']+=1
            with self.assertRaises(ValueError):contract.compose_expected_records(bad,{'snow_deposition':snow,'mountain_detail':True})
            batches=self.variants[True,snow];m={'features':{'mountain_detail':True,'snow_deposition':snow},'mountainDetail':{},'detail':{'landscapeTriangles':10000}}
            restored,manifest=restore_prior_mountains(batches,m)
            self.assertEqual([raw_attributes(b) for b in restored],[raw_attributes(b) for b in self.variants[False,snow]])
            self.assertNotIn('mountain_detail',manifest['features']);self.assertEqual(manifest['features']['snow_deposition'],snow)

    def test_current_native_matches_manifest_gate(self):
        data=ROOT/'Assets/TreeTopYokocho/Data';manifest=json.loads((data/'WorldManifest.json').read_text())
        from mountain_quality_contract import validate_native_mountains
        result=validate_native_mountains(read_visual(data/'VisualMeshes.bytes'),manifest.get('features',{}));self.assertTrue(result['passed'],result)

if __name__=='__main__':unittest.main(verbosity=2)
