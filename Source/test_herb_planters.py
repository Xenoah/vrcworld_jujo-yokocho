"""Focused botanical source/mesh contracts; no world generation or runtime test.

Run with the project Python: python Source/test_herb_planters.py
Only the two compact legacy geometry functions below are pinned references.
They preserve the v2.9.0 plant() and high_detail.leaf() geometry used before
herb_planters.py. Dependencies/material names are bound locally for isolation;
no historical whole builder, generated world or staging directory is required.
"""
from pathlib import Path
import ast
import copy
import json
import math
import unittest

import numpy as np
from PIL import Image
import herb_planters
import world_geometry
from herb_planters import add_herb_planter, _leaf
from world_geometry import Geometry

SOURCE = Path(world_geometry.__file__).resolve().parent
TEXTURES = SOURCE.parent / 'Assets' / 'TreeTopYokocho' / 'Textures'


def _legacy_leaf(g, p, right, length, material, scale=1):
    """Pinned v2.9.0 high_detail.leaf geometry, predating this feature."""
    p=np.array(p);r=np.array(right);l=np.array(length);normal=np.cross(r,l);normal/=max(np.linalg.norm(normal),1e-8)
    v=[];uv=[];faces=[]
    for k in range(7):
        t=k/6;width=math.sin(math.pi*t)**.82*(1+.07*(-1)**k)
        mid=p+l*(t-.5)+normal*(math.sin(math.pi*t)*.026*scale)
        for j in [-1,0,1]:
            v.append(mid+r*width*j+normal*(abs(j)*-.018*scale));uv.append(((j*width+1)/2,t))
        if k:
            b=(k-1)*3
            faces.extend([(b,b+1,b+4),(b,b+4,b+3),(b+1,b+2,b+5),(b+1,b+5,b+4)])
    g.add(v,faces,material,uv)


def _legacy_plant(g, pos, size, rng):
    """Pinned v2.9.0 build_world.plant body, with explicit isolated bindings."""
    food='Food';dark='DarkTimber';leafs=['Foliage'+str(i) for i in range(4)]
    p=np.array(pos);g.cylinder(p+[0,0,.14*size],.20*size,.28*size,food,24,r2=.24*size)
    for j in range(10):
        a=j*math.tau/10;tip=p+np.array([math.cos(a)*.24,math.sin(a)*.24,.48+rng.random()*.28])*size
        g.tube([p+[0,0,.25*size],tip],[.013*size,.003*size],dark,6)
        for k in range(3):
            q=p+[0,0,.25*size]+(tip-p-[0,0,.25*size])*(.5+k*.22)
            _legacy_leaf(g,q,[math.sin(a)*.065*size,-math.cos(a)*.065*size,0],[math.cos(a)*.19*size,math.sin(a)*.19*size,.02],leafs[j%4])


def _geometry():
    g=Geometry()
    g.material('Food',(.58,.25,.075),roughness=.33)
    g.material('DarkTimber',(.56,.42,.29),'PBR/wood_planks_grey_diff_4k.jpg',roughness=1,
               normal='PBR/wood_planks_grey_nor_gl_2k.jpg',arm='PBR/wood_planks_grey_arm_2k.jpg',uvScale=.65)
    for i,color in enumerate([(.72,.82,.52),(.77,.90,.58),(.87,.93,.62),(.62,.82,.54)]):
        g.material('Foliage'+str(i),color,'leaf.png',roughness=.83,
                   normal='leaf_detail_normal.png',arm='leaf_detail_arm.png',shader='Foliage')
    return g


def _build(idx, pos=(0,0,0), size=.65, legacy=False, rng=None):
    g=_geometry();g.group=f'Shops/S{idx+1:02d}'
    fn=_legacy_plant if legacy else add_herb_planter
    fn(g,pos,size,np.random.default_rng(12040+idx) if rng is None else rng)
    return g


class _ScalarDraws:
    def __init__(self):
        self.calls=[]

    def random(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return .37


def _plant_callsite_contract(tree):
    """One exact placement per shop, including mutually exclusive new branch."""
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='plant']
    expected=ast.parse('plant(P(w/2-.3,dep/2+.3,0),.65)',mode='eval').body
    same=lambda a,b:ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    if len(calls) not in (1,2) or any(not same(c,expected) for c in calls):raise ValueError('Unexpected plant placement/call count')
    loops=[n for n in tree.body if isinstance(n,ast.For) and ast.unparse(n.iter)=="enumerate(layout['shops'])"]
    if len(loops)!=1:raise ValueError('Expected one authoritative shop loop')
    loop=loops[0]
    if any(c not in list(ast.walk(loop)) for c in calls):raise ValueError('Plant call outside shop loop')
    direct=lambda body:[n.value for n in body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and n.value in calls]
    if len(calls)==1:
        if direct(loop.body)!=calls:raise ValueError('Legacy plant call is not unconditional per shop')
        return 'legacy_one_call'
    gate=ast.parse("FEATURES.get('shop_personality') is True",mode='eval').body
    branches=[n for n in loop.body if isinstance(n,ast.If) and same(n.test,gate)]
    if len(branches)!=1:raise ValueError('Replacement plant call requires literal-true shop branch')
    branch=branches[0]
    if branch.orelse or not branch.body or not isinstance(branch.body[-1],ast.Continue):raise ValueError('Replacement branch must terminate with continue')
    if sum(isinstance(n,ast.Continue) for n in ast.walk(branch))!=1:raise ValueError('Unexpected nested branch continuation')
    inside=direct(branch.body);outside=direct(loop.body)
    if len(inside)!=1 or len(outside)!=1 or set(inside+outside)!=set(calls):raise ValueError('Expected one direct call in each exclusive branch')
    if loop.body.index(branch)>=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Expr) and n.value is outside[0]):raise ValueError('Legacy call must follow terminated replacement branch')
    return 'literal_feature_branch_and_legacy_fallback'


class HerbPlanterContracts(unittest.TestCase):
    def test_current_builder_wrapper_and_callsite(self):
        # Permit version, feature and unrelated owner edits. Verify only the
        # public botanical wrapper and its one original per-shop placement.
        tree=ast.parse((SOURCE/'build_world.py').read_text())
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='plant']
        self.assertEqual(len(functions),1)
        expected=ast.parse('def plant(pos,size=.8):\n    add_herb_planter(g,pos,size,rng)').body[0]
        self.assertEqual(ast.dump(functions[0],include_attributes=False),
                         ast.dump(expected,include_attributes=False))
        imports=[n for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=='herb_planters']
        self.assertTrue(any(a.name=='add_herb_planter' and a.asname is None for n in imports for a in n.names))
        self.assertIn(_plant_callsite_contract(tree),('legacy_one_call','literal_feature_branch_and_legacy_fallback'))
        shops=json.loads((SOURCE/'layout.reference.json').read_text())['shops']
        self.assertEqual([s['id'] for s in shops],[f'S{i:02d}' for i in range(1,9)])

    def test_mutually_exclusive_replacement_branch_rejects_weakenings(self):
        source="""for idx,s in enumerate(layout['shops']):
    if FEATURES.get('shop_personality') is True:
        plant(P(w/2-.3,dep/2+.3,0),.65)
        continue
    plant(P(w/2-.3,dep/2+.3,0),.65)
"""
        self.assertEqual(_plant_callsite_contract(ast.parse(source)),'literal_feature_branch_and_legacy_fallback')
        mutations=[source.replace('        continue\n',''),source.replace(' is True'," == 'true'"),source.replace('w/2-.3','w/2-.2',1),source+"plant(P(w/2-.3,dep/2+.3,0),.65)\n",source.replace("    plant(P(w/2-.3,dep/2+.3,0),.65)\n","    if True:\n        plant(P(w/2-.3,dep/2+.3,0),.65)\n",1)]
        for value in mutations:
            with self.assertRaises((ValueError,SyntaxError)):_plant_callsite_contract(ast.parse(value))

    def test_exact_ten_scalar_rng_draws_and_state(self):
        for seed in (0,1,12040,992391):
            old=np.random.default_rng(seed);new=np.random.default_rng(seed)
            for idx in range(8):
                _build(idx,legacy=True,rng=old);_build(idx,rng=new)
                self.assertEqual(old.bit_generator.state,new.bit_generator.state)
            self.assertEqual(old.random(),new.random())
        rng=_ScalarDraws();g=_geometry()
        self.assertIsNone(add_herb_planter(g,[0,0,0],rng=rng))
        self.assertEqual(rng.calls,[((),{})]*10)

    def test_existing_batches_materials_and_group_unchanged(self):
        g=_geometry();g.group='Shops/S03';g.box([7,8,9],[1,1,1],'Food')
        batches=copy.deepcopy(g.batches);materials=copy.deepcopy(g.materials)
        add_herb_planter(g,[0,0,0],.65,np.random.default_rng(7))
        self.assertEqual(g.group,'Shops/S03')
        for key,batch in batches.items():
            self.assertEqual(batch,g.batches[key])
        for name,material in materials.items():
            self.assertEqual(material,g.materials[name])

    def test_original_centers_footprints_heights_and_static_materials(self):
        shops=json.loads((SOURCE/'layout.reference.json').read_text())['shops']
        for idx,shop in enumerate(shops):
            a=math.radians(shop['front_deg']);normal=np.array([math.cos(a),math.sin(a),0])
            side=np.array([normal[1],-normal[0],0])
            p=np.array([shop['x'],shop['y'],shop['z']])+side*(shop['width']/2-.3)+normal*(shop['depth']/2+.3)
            for size in (.4,.65,.8,1):
                old=_build(idx,p,size,legacy=True);new=_build(idx,p,size)
                ov=np.concatenate([b['v'] for b in old.batches.values()])
                nv=np.concatenate([b['v'] for b in new.batches.values()])
                self.assertTrue(np.all(nv[:,:2].min(0)>=ov[:,:2].min(0)-1e-10))
                self.assertTrue(np.all(nv[:,:2].max(0)<=ov[:,:2].max(0)+1e-10))
                self.assertAlmostEqual(float(nv[:,2].min()),float(p[2]))
                if size in (.65,.8):
                    self.assertLess(float(nv[:,2].max()-p[2]),1)
                for _,material in new.batches:
                    self.assertNotEqual(new.materials[material].get('shader'),'Foliage')

    def test_finite_valid_non_degenerate_geometry(self):
        for idx in range(8):
            for key,batch in _build(idx).batches.items():
                v=np.array(batch['v']);f=np.array(batch['f']);uv=np.array(batch['uv'])
                self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(uv).all())
                self.assertTrue((f>=0).all());self.assertTrue((f<len(v)).all())
                area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
                self.assertTrue((area>1e-12).all(),(key,float(area.min())))

    def test_only_existing_shared_texture_files(self):
        shared={'tile_clay_normal.png','tile_clay_arm.png','PBR/rocky_terrain_02_diff_4k.jpg',
                'PBR/rocky_terrain_02_nor_gl_2k.jpg','leaf.png','leaf_detail_normal.png','leaf_detail_arm.png'}
        for material in _build(0).materials.values():
            for field in ('texture','normal','arm'):
                if material.get(field):
                    self.assertTrue((TEXTURES/material[field]).is_file(),material[field])
                    if material['name'].startswith('Herb'):
                        self.assertIn(material[field],shared)

    def test_opaque_leaf_geometry_with_independent_backfaces(self):
        with Image.open(TEXTURES/'leaf.png') as image:
            self.assertEqual(image.mode,'RGB')
        g=Geometry();g.material('Leaf',(.5,.5,.5))
        _leaf(g,np.array([0.,0.,0.]),np.array([.1,0,.02]),.04,'Leaf',.12)
        batch=g.batches[('World','Leaf')];v=np.array(batch['v']);f=np.array(batch['f'])
        nv=len(v)//2;nf=len(f)//2
        np.testing.assert_array_equal(v[:nv],v[nv:])
        np.testing.assert_array_equal(f[nf:],f[:nf,::-1]+nv)
        for idx in range(8):
            for name,material in _build(idx).materials.items():
                if name.startswith('HerbLeaf'):
                    self.assertFalse(material.get('alphaClip'))
                    self.assertNotIn('alphaMode',material)
                    self.assertFalse(material.get('shader'))

    def test_hollow_pot_lip_and_recessed_soil(self):
        for idx in range(8):
            g=_build(idx)
            soil=next(b for (_,m),b in g.batches.items() if m=='HerbSoil')
            self.assertLess(np.array(soil['v'])[:,2].max(),.241*.65)
            clay=next(b for (_,m),b in g.batches.items() if m.startswith('HerbClay'))
            v=np.array(clay['v']);self.assertGreater(v[:,2].max(),.279*.65)
            for face in clay['f']:
                q=v[face]
                self.assertFalse(np.all(q[:,2]>.25*.65) and np.any(np.linalg.norm(q[:,:2],axis=1)<.1*.65))

    def test_geometry_independent_of_prior_supplied_rng(self):
        for idx in range(8):
            self.assertEqual(_build(idx,rng=np.random.default_rng(1)).batches,
                             _build(idx,rng=np.random.default_rng(2)).batches)

    def test_production_uv_repair_is_bounded_and_finite(self):
        for idx in range(8):
            g=_build(idx);g.compact()
            self.assertEqual(g.repair_normal_uvs(),56)
            g.bake_mood([])
            for batch in g.batches.values():
                self.assertTrue(np.isfinite(batch['uv']).all())
                self.assertTrue(np.isfinite(batch['colors']).all())


if __name__=='__main__':
    unittest.main(verbosity=2)
