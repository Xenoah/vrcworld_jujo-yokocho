"""Regression tests for opt-in surface tint and UV-repaired vertex colors.

Run with: python Source/test_authored_tints.py
"""
import unittest
import random
import numpy as np
from world_geometry import Geometry
from high_detail import roof_tiles


class AuthoredTintTests(unittest.TestCase):
    def test_default_color32_bytes_match_previous_bake(self):
        rng=np.random.default_rng(771)
        for material in ('Kawara','Cedar','Bronze','Foliage3','ForestCanopy2'):
            g=Geometry();g.material(material,(1,1,1),normal='normal.png')
            v=rng.normal(size=(30,3));f=np.arange(30).reshape(-1,3)
            g.add(v,f,material,np.zeros((30,2)))
            g.compact();self.assertEqual(g.repair_normal_uvs(),10)
            b=next(iter(g.batches.values()));vertices=b['v']
            # Exact pre-hook calculation, including existing foliage shading.
            c=np.ones((len(vertices),3))
            if material.startswith(('Foliage','ForestCanopy')):
                variation=.79+.18*(.5+.5*np.sin(vertices[:,0]*.43+vertices[:,1]*.71+vertices[:,2]*.28))
                c*=variation[:,None]
            expected=np.column_stack([c,np.ones(len(vertices))]).astype(np.float32)
            g.bake_mood([])
            self.assertEqual((b['colors']*255).astype('u1').tobytes(),(expected*255).astype('u1').tobytes())
            self.assertEqual(len(b['colors']),len(vertices))

    def test_uv_repair_copies_each_tinted_corner(self):
        g=Geometry();g.material('Kawara',(1,1,1),normal='normal.png')
        g.add([(0,0,0),(1,0,0),(0,1,0)],[(0,1,2)],'Kawara',[(0,0)]*3)
        b=next(iter(g.batches.values()))
        # Different corners and overlapping ranges exercise exact tint products.
        b['authored_tints']=[(0,3,(.80,.78,.76)),(1,2,(.90,.95,1)),(2,3,(.85,.87,.89))]
        g.compact();g.bake_mood([]);expected=b['colors'].copy()
        self.assertEqual(g.repair_normal_uvs(),1)
        g.bake_mood([])
        self.assertEqual(len(b['v']),6);self.assertEqual(len(b['colors']),6)
        np.testing.assert_array_equal(b['colors'][:3],expected)
        np.testing.assert_array_equal(b['colors'][b['f'][0]],expected)
        self.assertEqual((b['colors'][3:]*255).astype('u1').tobytes(),(expected*255).astype('u1').tobytes())
        # A second no-op repair/bake must not multiply or append tint again.
        colors=b['colors'].copy();self.assertEqual(g.repair_normal_uvs(),0);g.bake_mood([])
        np.testing.assert_array_equal(b['colors'],colors)

    def test_roof_tints_are_bounded_opt_in_and_do_not_consume_rng(self):
        g=Geometry();g.material('Kawara',(.67,.72,.77),normal='normal.png');g.material('DarkTimber',(.56,.42,.29))
        g.group='Shops/Test';P=lambda x,y,z:np.array([x,y,z])
        py_before=random.getstate();np_before=np.random.get_state()
        roof_tiles(g,P,6,5.4,'Kawara','DarkTimber')
        self.assertEqual(random.getstate(),py_before)
        np_after=np.random.get_state()
        self.assertEqual(np_after[0],np_before[0]);np.testing.assert_array_equal(np_after[1],np_before[1]);self.assertEqual(np_after[2:],np_before[2:])
        g.compact();self.assertEqual(g.repair_normal_uvs(),0);g.bake_mood([])
        for (_,material),b in g.batches.items():
            self.assertEqual(len(b['colors']),len(b['v']))
            if material=='Kawara':
                self.assertGreaterEqual(float(b['colors'][:,:3].min()),.73)
                self.assertLessEqual(float(b['colors'][:,:3].max()),.85)
                self.assertGreater(len(np.unique((b['colors'][:,:3]*255).astype('u1'),axis=0)),8)
            else:
                self.assertTrue(np.all(b['colors']==1))


if __name__=='__main__':unittest.main(verbosity=2)
