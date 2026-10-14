"""Dispatcher boundary tests, independent of final authored venue payloads."""
import copy,unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import shop_personality as sp

class DispatcherTests(unittest.TestCase):
    def test_selective_legacy_material_prerequisites(self):
        g=SimpleNamespace(materials={})
        def material(**descriptor):
            g.materials[descriptor['name']]=copy.deepcopy(descriptor)
        g.material=material
        sp.retain_legacy_materials(g,('CraftSurfaces','CraftEmbers'))
        self.assertEqual(set(g.materials),{'CraftSurfaces','CraftEmbers'})
        old=copy.deepcopy(g.materials)
        sp.retain_legacy_materials(g)
        self.assertEqual(len(g.materials),98)
        for key,value in old.items():self.assertEqual(g.materials[key],value)
        sp.retain_legacy_materials(g)
    def test_legacy_rng_consumption(self):
        a=np.random.default_rng(12040);b=np.random.default_rng(12040)
        for _ in range(8):
            sp.consume_legacy_shop_rng(a)
            for _ in range(12):b.uniform(-.035,.035,2);b.uniform(-.03,.04)
            for _ in range(10):self.assertEqual(a.random(),b.random())
        self.assertEqual(a.bit_generator.state,b.bit_generator.state)
    def test_vector_rejects_invalid(self):
        for value in ([1,2],[1,2,float('nan')],[1,2,float('inf')],[True,2,3],'123',None):
            with self.assertRaises(ValueError):sp.vector(value,'test')
    def build(self,mutator=lambda x:None,geometry_mutator=lambda g:None):
        g=SimpleNamespace(batches={('Sentinel','Stone'):{'v':[[0.,0.,0.]],'f':[],'uv':[[0.,0.]],'authored_tints':[(0,1,np.array([.5,.6,.7]))]}},materials={'Stone':{'name':'Stone'}},group='Shops/S01');calls=[]
        result=dict(shop='S01',completeVisualReplacement=True,theme='test',seatOverrides=sp.default_seats(0,6,5.4),solids=[dict(name='wall',center=[1,2,1],size=[2,.2,2],yaw=90)],routes=[dict(name='entry',points=[[0,0,.06],[0,1,.06]],centerline=[[0,0],[0,1]],servicePoint=[0,1,.06])],lights=[dict(position=[0,0,2],range=5,strength=1)],steam=[])
        mutator(result)
        def build(*args,**kw):
            geometry_mutator(g)
            kw['lantern']([0,0,2],record=True)
            return result
        module=SimpleNamespace(build_venue=build,__file__=__file__)
        P=lambda x,y,z:np.array([10-y,20+x,34+z])
        stations=[];solids=[];lights=[];steam=[]
        with patch.object(sp.importlib,'import_module',return_value=module):
            row=sp.build_shop(g,P,None,dict(id='S01',width=6,depth=5.4),0,{},lambda *a,**kw:calls.append(kw),stations,solids,lights,steam)
        return row,stations,solids,lights,steam,calls
    def test_owned_light_and_solid_transform(self):
        row,stations,solids,lights,steam,calls=self.build()
        self.assertEqual(calls,[{'record':False}]);self.assertEqual(row['ownership']['lightIndices'],[0])
        np.testing.assert_allclose(solids[0]['center'],[8,21,35]);np.testing.assert_allclose(solids[0]['axes'],[-1,0,0,0,-1,0,0,0,1],atol=1e-15)
        self.assertEqual(len(stations),6)
    def test_finalize_keeps_local_and_transforms_world(self):
        row,stations,solids,lights,steam,calls=self.build();original=copy.deepcopy(row)
        for seq in (stations,solids,lights):
            for item in seq:
                for key in ('position','exit','center'):
                    if key in item:item[key][2]+=100
        final=sp.finalize([row],stations,solids,lights,steam,lambda z:z+100)['shops'][0]
        self.assertEqual(row,original);self.assertEqual(final['local'],row['local']);self.assertEqual(final['frame']['floorZ'],134)
        np.testing.assert_allclose(final['world']['routes'][0]['points'],[[10,20,134.06],[9,20,134.06]])
        np.testing.assert_allclose(final['world']['routes'][0]['servicePoint'],[9,20,134.06])
        self.assertNotIn('centerline',final['world']['routes'][0])
        self.assertIn('centerline',final['local']['routes'][0])
    def test_existing_batch_mutation_rejected(self):
        with self.assertRaises(ValueError):self.build(geometry_mutator=lambda g:g.batches[('Sentinel','Stone')]['v'][0].__setitem__(0,1))
    def test_existing_authored_tint_mutation_rejected(self):
        with self.assertRaises(ValueError):self.build(geometry_mutator=lambda g:g.batches[('Sentinel','Stone')]['authored_tints'][0][2].__setitem__(0,.1))
    def test_existing_material_mutation_rejected(self):
        with self.assertRaises(ValueError):self.build(geometry_mutator=lambda g:g.materials['Stone'].update(color=[1,0,0]))
    def test_literal_feature(self):
        for value in (1,0,'true',None,[]):
            with self.assertRaises(ValueError):sp.validate_feature({'shop_personality':value})
        for value in (True,False):sp.validate_feature({'shop_personality':value})
        sp.validate_feature({})
    def test_bad_station_roster_rejected(self):
        with self.assertRaises(ValueError):self.build(lambda x:x['seatOverrides'].pop())
    def test_nonliteral_replacement_rejected(self):
        with self.assertRaises(ValueError):self.build(lambda x:x.update(completeVisualReplacement=1))
    def test_unreviewed_light_color_rejected(self):
        with self.assertRaises(ValueError):self.build(lambda x:x['lights'][0].update(color=[1,0,0]))
    def test_nonpositive_solid_rejected(self):
        with self.assertRaises(ValueError):self.build(lambda x:x['solids'][0].update(size=[1,0,1]))
    def test_invalid_forward_rejected(self):
        with self.assertRaises(ValueError):self.build(lambda x:x['seatOverrides'][0].update(forward=[0,0,1]))

if __name__=='__main__':unittest.main()
