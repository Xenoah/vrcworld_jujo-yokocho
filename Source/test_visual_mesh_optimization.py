import unittest
import numpy as np
from visual_mesh_optimization import compact_unused_visual_vertices,simplify_planar_sea,SEA_KEYS
from world_geometry import Geometry

class CompactTests(unittest.TestCase):
    def test_order_attributes_seams_and_idempotence(self):
        g=Geometry();g.batches[('test','wood')]={'v':np.array([[.2,.2,0],[0,0,0],[1,0,0],[0,1,0],[0,0,0],[.3,.3,0]],np.float32),'uv':np.arange(12,dtype=np.float32).reshape(6,2),'colors':np.arange(24,dtype=np.float32).reshape(6,4)/255,'f':np.array([[1,2,3],[4,3,2]],np.uint32)}
        b=g.batches[('test','wood')];old={k:v.copy() for k,v in b.items()};r=compact_unused_visual_vertices(g)
        self.assertEqual(r['removedVertices'],2)
        for attr in ['v','uv','colors']:np.testing.assert_array_equal(old[attr][old['f']],b[attr][b['f']])
        # Coincident vertices 1 and 4 remain distinct, preserving normal seams.
        self.assertNotEqual(b['f'][0,0],b['f'][1,0]);self.assertEqual(compact_unused_visual_vertices(g)['removedVertices'],0)
    def test_identity_and_empty_batch_preserved(self):
        g=Geometry();g.add([[0,0,0]],[],'empty');r=compact_unused_visual_vertices(g)
        self.assertEqual(list(g.batches),[('World','empty')]);self.assertEqual(r['removedVertices'],1)


    def test_unused_bounds_anchors_retained(self):
        g=Geometry();g.add([[9,9,9],[0,0,0],[1,0,0],[0,1,0],[.5,.5,0]],[[1,2,3]],'m')
        r=compact_unused_visual_vertices(g);self.assertEqual(r['removedVertices'],1)
        np.testing.assert_array_equal(g.batches[('World','m')]['v'].max(axis=0),[9,9,9])

class PlanarSeaTests(unittest.TestCase):
    def fixture(self):
        from fantasy_landscape import _sea
        g=Geometry();_sea(g,{'lake':'Lake'});g.compact();g.bake_mood([]);return g
    def test_four_exact_boundaries_and_positive_normals(self):
        from measure_visual_optimization import boundary
        g=self.fixture()
        def native(b):return dict(vertices=b['v'],uv=b['uv'],colors=np.uint8(b['colors']*255),faces=b['f'])
        before={k:boundary(native(b)) for k,b in g.batches.items()}
        r=simplify_planar_sea(g);self.assertEqual(r['removedTriangles'],5336)
        for k,b in g.batches.items():
            self.assertEqual(before[k],boundary(native(b)))
            q=b['v'][b['f']].astype(float);n=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);self.assertTrue(np.all(n[:,2]>0))
    def test_refuse_nonplanar_or_colored_or_unknown_topology(self):
        for mutation in ['height','color','topology','uv']:
            g=self.fixture();b=g.batches[SEA_KEYS[0]]
            if mutation=='height':b['v'][200,2]+=.1
            if mutation=='color':b['colors'][200,0]=.5
            if mutation=='uv':b['uv'][200,0]+=.1
            if mutation=='topology':b['f']=b['f'][:-1]
            with self.assertRaises(ValueError):simplify_planar_sea(g)

if __name__=='__main__':unittest.main()

