"""Portable additive, mechanical and topology tests; not Unity/VRChat validation."""
import copy, hashlib, json, math, pickle, random, unittest
from pathlib import Path
import numpy as np
import trimesh
from world_geometry import Geometry
from venue_projecting_signs import add_signs, FOOTPRINTS
ROOT=Path(__file__).resolve().parent
M=dict(iron='Iron',trim='Bronze',night_walnut='Night_Walnut',night_wine='Night_WineUpholstery',night_glass='Night_SmokyGlass')
DESCRIPTORS=json.loads((ROOT/'testdata/projecting_signs_materials.json').read_text())

def make(idx, angle=0, offset=(0,0,0)):
    g=Geometry();g.materials={m['name']:copy.deepcopy(m) for m in DESCRIPTORS}
    g.group='Sentinel';g.box([17,19,23],[.2,.3,.4],'Iron');g.group=f'Shops/S{idx+1:02d}'
    o=np.array(offset);a=math.cos(angle);b=math.sin(angle)
    basis=np.array([[a,-b,0],[b,a,0],[0,0,1.]])
    P=lambda x,y,z:o+basis@np.array([x,y,z])
    material_before=copy.deepcopy(g.materials);mapping=copy.deepcopy(M);sentinel=copy.deepcopy(g.batches)
    result=add_signs(g,P,idx,M,*FOOTPRINTS[idx])
    return g,result,P,basis,material_before,mapping,sentinel

class ProjectingSignTests(unittest.TestCase):
    def test_repeat_and_no_global_rng_changes(self):
        np_before=np.random.get_state();py_before=random.getstate()
        for i in range(8):
            a,ma,*_=make(i);b,mb,*_=make(i)
            self.assertEqual(ma,mb);self.assertEqual(pickle.dumps(a.batches),pickle.dumps(b.batches))
        self.assertEqual(py_before,random.getstate())
        self.assertTrue(all(np.array_equal(a,b) for a,b in zip(np_before,np.random.get_state())))

    def test_existing_geometry_materials_mapping_and_group_unchanged(self):
        for i in range(8):
            g,m,P,basis,materials,mapping,sentinel=make(i)
            self.assertEqual(g.materials,materials);self.assertEqual(M,mapping)
            self.assertEqual(g.group,f'Shops/S{i+1:02d}')
            for key,old in sentinel.items():self.assertEqual(g.batches[key],old)
            for key in set(g.batches)-set(sentinel):
                self.assertTrue(key[0].startswith(f'Shops/S{i+1:02d}/ProjectingSigns/'))

    def test_metadata_exact_and_budget(self):
        total=0
        for i in range(8):
            g,m,*_=make(i);total+=m['triangleCount'];json.dumps(m,allow_nan=False)
            keys=[k for k in g.batches if k[0]!='Sentinel']
            self.assertEqual(m['keys'],[list(k) for k in keys]);self.assertEqual(m['batchCount'],len(keys))
            self.assertEqual(m['triangleCount'],sum(len(g.batches[k]['f']) for k in keys))
            self.assertEqual(m['sourceVertexCount'],sum(len(g.batches[k]['v']) for k in keys))
            for part in m['parts']:
                bs=[b for (gr,mat),b in g.batches.items() if gr==part['group']]
                vv=np.concatenate([np.asarray(b['v']) for b in bs])
                np.testing.assert_allclose(part['localBounds'],[vv.min(0),vv.max(0)],atol=1e-11)
                self.assertEqual(part['triangles'],sum(len(b['f']) for b in bs))
        self.assertLess(total,10000)

    def test_rigid_transform_covariance(self):
        for i in range(8):
            g,m,*_=make(i);h,n,P,R,*_=make(i,.731,(13.7,-19.2,40.))
            self.assertEqual(m,n)
            for key,b in g.batches.items():
                if key[0]=='Sentinel':continue
                vv=np.asarray(b['v']);expected=vv@R.T+np.array([13.7,-19.2,40.])
                np.testing.assert_allclose(h.batches[key]['v'],expected,atol=1e-12)
                np.testing.assert_array_equal(b['f'],h.batches[key]['f'])
                np.testing.assert_allclose(b['uv'],h.batches[key]['uv'],atol=1e-12)

    def test_finite_non_degenerate_closed_outward_geometry(self):
        for i in range(8):
            g,m,*_=make(i)
            for (group,mat),b in g.batches.items():
                if group=='Sentinel':continue
                with self.subTest(shop=i,group=group,material=mat):
                    v=np.asarray(b['v']);f=np.asarray(b['f']);uv=np.asarray(b['uv'])
                    self.assertTrue(np.isfinite(v).all() and np.isfinite(uv).all())
                    self.assertEqual(len(v),len(uv));self.assertLess(f.max(),len(v));self.assertGreaterEqual(f.min(),0)
                    q=v[f];area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
                    self.assertGreater(area.min(),1e-11)
                    mesh=trimesh.Trimesh(v,f,process=True)
                    # Several separate closed support solids meet exactly. A
                    # weld can create 4-way interior edges, but no naked edge.
                    incidence=np.bincount(mesh.edges_unique_inverse)
                    self.assertTrue((incidence>=2).all())
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertGreater(mesh.volume,0)

    def test_height_and_owned_roof_lateral_bounds(self):
        for i in range(8):
            g,m,*_=make(i);w,dep=FOOTPRINTS[i]
            vv=np.concatenate([np.asarray(b['v']) for (gr,mat),b in g.batches.items() if gr!='Sentinel'])
            self.assertGreaterEqual(vv[:,2].min(),2.30)
            # The narrowest owned food roof is 0.16 m beyond the side wall;
            # S03 also has 47 mm seam tubes, so its physical extent is 0.207 m.
            lateral={0:.23,1:.24,2:.207,3:.55,4:.24,5:.55,6:.55,7:.24}[i]
            self.assertGreaterEqual(vv[:,0].min(),-w/2-lateral)
            self.assertLessEqual(vv[:,0].max(),w/2+lateral)

    def test_brackets_actually_overlap_original_posts(self):
        for i in range(8):
            g,m,*_=make(i);w,dep=FOOTPRINTS[i]
            b=next(b for (group,mat),b in g.batches.items() if group.startswith(f'Shops/S{i+1:02d}/ProjectingSigns/') and mat=='Iron')
            # First primitive is the chamfered 0.028 x 0.12 x 0.28 m mounting base.
            vv=np.array(b['v'][:96]);lo,hi=vv.min(0),vv.max(0)
            post_half=.10 if i in (3,5,6) else .09
            postheight={0:3.12,1:2.72,2:2.64,3:2.8,4:2.79,5:2.8,6:2.8,7:2.85}[i]
            pl=np.array([-w/2+.1-post_half,dep/2-post_half,0]);ph=np.array([-w/2+.1+post_half,dep/2+post_half,postheight])
            self.assertTrue((np.minimum(hi,ph)-np.maximum(lo,pl)>0).all())

    def test_duplicate_namespace_rejected_without_append(self):
        for i in range(8):
            g,m,P,*_=make(i);old=pickle.dumps(g.batches)
            with self.assertRaises(ValueError):add_signs(g,P,i,M,*FOOTPRINTS[i])
            self.assertEqual(old,pickle.dumps(g.batches))

    def test_exact_consolidation_component_ranges(self):
        import venue_projecting_signs as signs
        from unittest.mock import patch
        saved=0
        for i in range(8):
            with patch.object(signs,'_consolidate',lambda g,r:r):
                original,om,*_=make(i)
            g,m,*_=make(i);saved+=m['consolidation']['removedBatchCount']
            for component in m['parts'][0]['components']:
                for r in component['ranges']:
                    target=g.batches[tuple(r['key'])]
                    source=original.batches[(m['root']+'/'+component['semantic'],r['key'][1])]
                    a=r['vertexStart'];b=a+r['vertexCount'];fa=r['triangleStart'];fb=fa+r['triangleCount']
                    np.testing.assert_array_equal(target['v'][a:b],source['v'])
                    np.testing.assert_array_equal(target['uv'][a:b],source['uv'])
                    np.testing.assert_array_equal(np.array(target['f'][fa:fb])-a,source['f'])
        self.assertEqual(saved,19)

    def test_invalid_inputs_before_any_mutation(self):
        g=Geometry();P=lambda x,y,z:[x,y,z]
        for idx in (True,None,-1,8,'4'):
            with self.assertRaises(ValueError):add_signs(g,P,idx,M,7.2,6.)
        with self.assertRaises(ValueError):add_signs(g,P,4,M,7.,6.)
        self.assertFalse(g.batches)

if __name__=='__main__':unittest.main(verbosity=2)
