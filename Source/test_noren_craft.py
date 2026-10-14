"""Portable isolated contracts. No world generation, edits, network, or renderer.

YOKOCHO_PROJECT=/path/to/project python Source/test_noren_craft.py
The staged module directory must precede project/Source on PYTHONPATH when this
file is tested before integration. Integrated use resolves adjacent modules.
"""
from pathlib import Path
import os,sys,json,copy,hashlib,math,random,inspect,unittest,argparse
from unittest import mock
import numpy as np
HERE=Path(__file__).resolve().parent
_parser=argparse.ArgumentParser(add_help=False)
_parser.add_argument('--project',type=Path,default=Path(os.environ.get('YOKOCHO_PROJECT',HERE.parent)))
_parser.add_argument('--report',type=Path)
_parser.add_argument('--check-current-native',action='store_true')
OPTIONS,UNIT_ARGS=_parser.parse_known_args()
PROJECT=OPTIONS.project
sys.dont_write_bytecode=True
sys.path.append(str(PROJECT/'Source'))
from world_geometry import Geometry
import shopfront_identity as shopfront
import noren_craft as craft

M=dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',iron='Iron')
LAYOUT=json.loads((PROJECT/'Source/layout.reference.json').read_text())['shops']
MANIFEST=json.loads((PROJECT/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
FIXTURE_PATH=HERE/'noren_legacy_fixture.json'
FIXTURE_SHA256='f2857028b761226f86f2dcccc0b4293b70c586c6afbd5ccb61506c3911f600a4'
FIXTURE=json.loads(FIXTURE_PATH.read_text())
_MISSING=object()

# Separately reviewed print-only composition, not a rewrite of the legacy
# fixture. The full print contract independently re-bakes the frozen original,
# requires its shipped PNG digest, and proves background/wording/mesh invariants.
PRINT_AA_FUNCTION_SHA256='631a9791dc5d46700e6efdc3fe8a42e9dd8a77b3e161565c9f2d9b486438426e'
PRINT_AA_MODULE_SHA256='3b65a398b9cac15c136666dd0a585c719095a48f38a4985617b6fd652e6c01f0'


def _check_legacy_function_hashes(actual,module_sha256,features):
    if not isinstance(features,dict):raise ValueError('Feature manifest must be an object')
    enabled=features.get('shopfront_print_aa',False)
    if type(enabled) is not bool:raise ValueError('shopfront_print_aa must be a literal Boolean')
    expected=dict(FIXTURE['function_sha256'])
    if enabled is True:
        # Only this one reviewed function differs; pin the complete admitted
        # module too so a changed print wrapper cannot inherit this exception.
        expected['make_shopfront_atlas']=PRINT_AA_FUNCTION_SHA256
        if module_sha256!=PRINT_AA_MODULE_SHA256:raise ValueError('Unreviewed print-AA source module')
    if actual!=expected:raise ValueError('Legacy shopfront source contract differs from its exact admitted state')


class RecordingGeometry(Geometry):
    def __init__(self):
        super().__init__();self.events=[]
        self.materials={m['name']:copy.deepcopy(m) for m in MANIFEST['materials']}
    def add(self,v,f,m,uv=None):
        self.events.append((self.group,m,np.asarray(v).copy(),np.asarray(f).copy(),None if uv is None else np.asarray(uv).copy()))
        super().add(v,f,m,uv)

def digest_arrays(*arrays):
    h=hashlib.sha256()
    for a in arrays:
        a=np.asarray(a)
        dt='<u4' if a.dtype.kind in 'iu' else '<f4'
        h.update(np.asarray(a,dtype=dt).tobytes())
    return h.hexdigest()

def digest_batch(b):return digest_arrays(b['v'],b['f'],b['uv'])
def event_signature(e):return (e[0],e[1],digest_arrays(e[2],e[3],e[4]))
def fingerprint(g):return [(a,b,digest_batch(v)) for (a,b),v in g.batches.items()]
def build(idx,enabled=_MISSING,noren_only=False,rng=None):
    g=RecordingGeometry();g.group='Shops/'+LAYOUT[idx]['id'];s=LAYOUT[idx]
    def P(x,y,z):return np.array([x,y,z],float)
    def B(x,y,z,w,d,h,ma):g.box(P(x,y,z),(w,d,h),ma)
    if noren_only:
        g.group+='/Identity';m=shopfront._materials(g)
        fn=craft.add_crafted_noren if enabled is True else shopfront._folded_noren
        fn(g,P,B,s['width'],s['depth'],idx,M,m,staff_entry=True)
    else:
        kwargs={} if enabled is _MISSING else {'noren_craft':enabled}
        shopfront.add_shopfront_identity(g,P,B,s['width'],s['depth'],idx,M,rng=rng,staff_entry=True,**kwargs)
    return g

class NorenCraftContracts(unittest.TestCase):
    def test_legacy_fixture_file_is_pinned(self):
        self.assertEqual(hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),FIXTURE_SHA256)

    def test_legacy_functions_are_source_exact(self):
        actual={name:hashlib.sha256(inspect.getsource(getattr(shopfront,name)).encode()).hexdigest()
                for name in FIXTURE['function_sha256']}
        module_sha256=hashlib.sha256(Path(shopfront.__file__).read_bytes()).hexdigest()
        _check_legacy_function_hashes(actual,module_sha256,MANIFEST.get('features',{}))

    def test_print_source_admission_is_literal_and_exact(self):
        original=dict(FIXTURE['function_sha256'])
        accepted=dict(original,make_shopfront_atlas=PRINT_AA_FUNCTION_SHA256)
        # Missing/off still demands the immutable original source hashes.
        for features in [{},{'shopfront_print_aa':False}]:
            _check_legacy_function_hashes(original,'legacy module',features)
            with self.assertRaises(ValueError):_check_legacy_function_hashes(accepted,PRINT_AA_MODULE_SHA256,features)
        _check_legacy_function_hashes(accepted,PRINT_AA_MODULE_SHA256,{'shopfront_print_aa':True})
        with self.assertRaises(ValueError):_check_legacy_function_hashes(original,PRINT_AA_MODULE_SHA256,{'shopfront_print_aa':True})
        for value in [None,0,1,'true',np.bool_(True),[],{}]:
            with self.subTest(flag=repr(value)),self.assertRaises(ValueError):
                _check_legacy_function_hashes(accepted,PRINT_AA_MODULE_SHA256,{'shopfront_print_aa':value})
        for features in [None,[],True]:
            with self.assertRaises(ValueError):_check_legacy_function_hashes(accepted,PRINT_AA_MODULE_SHA256,features)

    def test_print_admission_rejects_mutated_or_extra_source_hashes(self):
        for enabled in [False,True]:
            expected=dict(FIXTURE['function_sha256'])
            if enabled:expected['make_shopfront_atlas']=PRINT_AA_FUNCTION_SHA256
            for name in expected:
                changed=dict(expected);changed[name]='0'*64
                with self.subTest(enabled=enabled,function=name),self.assertRaises(ValueError):
                    _check_legacy_function_hashes(changed,PRINT_AA_MODULE_SHA256,{'shopfront_print_aa':enabled})
            for changed in [dict(expected,unapproved_function='0'*64),{k:v for k,v in expected.items() if k!='make_shopfront_atlas'}]:
                with self.assertRaises(ValueError):_check_legacy_function_hashes(changed,PRINT_AA_MODULE_SHA256,{'shopfront_print_aa':enabled})
        accepted=dict(FIXTURE['function_sha256'],make_shopfront_atlas=PRINT_AA_FUNCTION_SHA256)
        with self.assertRaises(ValueError):_check_legacy_function_hashes(accepted,'0'*64,{'shopfront_print_aa':True})

    def test_missing_false_and_nonliteral_flags_are_byte_exact(self):
        for idx in range(8):
            expected=[tuple(x) for x in FIXTURE['shops'][idx]['disabledFingerprint']]
            for enabled in [_MISSING,False,None,0,1,'true',np.bool_(True),{},[]]:
                with self.subTest(shop=idx,flag=repr(enabled)):
                    self.assertEqual(fingerprint(build(idx,enabled)),expected)

    def test_old_path_does_not_import_new_module(self):
        # The branch is verified syntactically as well as with truthy values.
        src=inspect.getsource(shopfront.add_shopfront_identity)
        self.assertIn('if noren_craft is True:',src)
        self.assertIn('else:\n        _folded_noren(',src)
        self.assertNotIn('rng.',inspect.getsource(craft.add_crafted_noren))
        original_import=__import__
        def guarded(name,*args,**kwargs):
            if name=='noren_craft':raise ImportError('New module deliberately unavailable')
            return original_import(name,*args,**kwargs)
        with mock.patch('builtins.__import__',side_effect=guarded):
            build(0)  # The argument is genuinely omitted.
            build(0,False)
            with self.assertRaises(ImportError):build(0,True)

    def test_rng_states_are_untouched(self):
        before_py=random.getstate();before_np=np.random.get_state()
        passed_rng=np.random.default_rng(91477);before_passed=copy.deepcopy(passed_rng.bit_generator.state)
        for idx in range(8):
            build(idx,True,rng=passed_rng)
        self.assertEqual(random.getstate(),before_py)
        after_np=np.random.get_state()
        self.assertEqual(before_np[0],after_np[0]);np.testing.assert_array_equal(before_np[1],after_np[1]);self.assertEqual(before_np[2:],after_np[2:])
        self.assertEqual(passed_rng.bit_generator.state,before_passed)
        # No random library or generator is used by the new module at all.
        src=inspect.getsource(craft)
        self.assertNotIn('np.random',src);self.assertNotIn('import random',src)

    def test_determinism_and_finite_geometry(self):
        for idx in range(8):
            g=build(idx,True);self.assertEqual(fingerprint(g),fingerprint(build(idx,True)))
            for key,b in g.batches.items():
                v=np.asarray(b['v']);f=np.asarray(b['f']);u=np.asarray(b['uv'])
                self.assertTrue(np.isfinite(v).all() and np.isfinite(u).all(),key)
                self.assertGreaterEqual(f.min(),0);self.assertLess(f.max(),len(v))
                q=v[f];area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
                self.assertGreater(float(area.min()),1e-12,(idx,key))

    def test_rolled_entry_and_pole_ties_exact(self):
        # Every original rolled-cloth event and its two tied straps precede the
        # normal panels; source helper itself is also protected by hash above.
        for idx in range(8):
            a=build(idx,False,True);b=build(idx,True,True)
            self.assertEqual([event_signature(x) for x in a.events[:13]],[event_signature(x) for x in b.events[:13]])
            self.assertEqual([event_signature(x) for x in a.events[-2:]],[event_signature(x) for x in b.events[-2:]])
            old=a.batches[(a.group,'ShopfrontTextile')];new=b.batches[(b.group,'ShopfrontTextile')]
            for k,n in [('v',417),('uv',417),('f',708)]:
                np.testing.assert_array_equal(np.asarray(old[k])[:n],np.asarray(new[k])[:n])

    def test_fascia_lamp_menus_exact_component_events(self):
        for idx in range(8):
            old_n=len(build(idx,False,True).events);new_n=len(build(idx,True,True).events)
            old=build(idx,False).events[old_n:];new=build(idx,True).events[new_n:]
            self.assertEqual([event_signature(e) for e in old],[event_signature(e) for e in new])

    def test_exact_affected_batch_roster_and_material_cost(self):
        total_old=total_new=0;added=removed=changed=0
        for idx in range(8):
            a=build(idx,False);b=build(idx,True);group='Shops/'+LAYOUT[idx]['id']+'/Identity'
            diff={key for key in a.batches.keys()|b.batches.keys() if key not in a.batches or key not in b.batches or digest_batch(a.batches[key])!=digest_batch(b.batches[key])}
            expected={(group,m) for m in ['ShopfrontTextile','DarkTimber','Counter','CraftSurfaces']}
            self.assertEqual(diff,expected)
            self.assertEqual(a.materials,b.materials)
            total_old+=sum(len(q['f']) for q in a.batches.values());total_new+=sum(len(q['f']) for q in b.batches.values())
            added+=len(b.batches.keys()-a.batches.keys());removed+=len(a.batches.keys()-b.batches.keys());changed+=len(diff)
        self.assertEqual(added,8);self.assertEqual(removed,5);self.assertEqual(changed,32)
        self.assertLess(total_new-total_old,22000)

    def test_all_panels_stay_in_measured_old_bounds_and_normals(self):
        import trimesh
        for idx,s in enumerate(LAYOUT):
            width=s['width']-.9;count=shopfront.IDENTITIES[idx]['panels'];y=s['depth']/2+.135
            for panel in range(1,count):
                x0=-width/2+width*panel/count+.014;x1=-width/2+width*(panel+1)/count-.014
                g=RecordingGeometry();g.group='Panel'
                craft._panel(g,lambda *p:np.array(p),x0,x1,y,width,panel,idx*.27,shopfront._rect(idx,'cloth'),'ShopfrontTextile',shopfront._uv)
                b=g.batches[('Panel','ShopfrontTextile')];v=np.asarray(b['v']);f=np.asarray(b['f']);lo,hi=craft._old_panel_bounds(x0,x1,idx*.27,panel);lo[1]+=y;hi[1]+=y
                self.assertTrue((v.min(axis=0)>=lo-1e-9).all(),(idx,panel,v.min(axis=0),lo))
                self.assertTrue((v.max(axis=0)<=hi+1e-9).all(),(idx,panel,v.max(axis=0),hi))
                # First two calls are independently normaled front/rear shells.
                a=g.events[0];z=g.events[1]
                for e,sgn in [(a,1),(z,-1)]:
                    q=e[2][e[3]];normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
                    self.assertGreater(float((normal[:,1]*sgn).min()),.85)
                self.assertTrue(np.all(np.asarray(a[2])[:,1]>np.asarray(z[2])[:,1]))
                mesh=trimesh.Trimesh(v,f,process=True)
                self.assertTrue(mesh.is_watertight,(idx,panel));self.assertTrue(mesh.is_winding_consistent,(idx,panel));self.assertGreater(mesh.volume,0)
                # Authored UV: U goes screen-right (-X) and V rises up the cloth.
                uv=a[4].reshape(8,17,2)
                self.assertTrue((np.diff(uv[:,:,0],axis=1)<0).all());self.assertTrue((np.diff(uv[:,:,1],axis=0)>0).all())
                self.assertTrue(((uv>=0)&(uv<=1)).all())

    def test_tab_and_rod_respect_old_union_bounds(self):
        import trimesh
        g=RecordingGeometry();g.group='Detail';P=lambda *p:np.array(p)
        craft._tab(g,P,0,0,5.1,shopfront._rect(0,'cloth'),'ShopfrontTextile',shopfront._uv)
        b=g.batches[('Detail','ShopfrontTextile')];v=np.asarray(b['v']);f=np.asarray(b['f'])
        self.assertLessEqual(abs(v[:,0]).max(),.008);self.assertGreaterEqual(v[:,2].min(),2.55);self.assertLessEqual(v[:,2].max(),2.647)
        for p in v:
            allowed=.0175 if 2.6075<=p[2]<=2.6425 else .014
            self.assertLessEqual(abs(p[1]),allowed)
        mesh=trimesh.Trimesh(v,f,process=True);self.assertTrue(mesh.is_watertight);self.assertTrue(mesh.is_winding_consistent);self.assertGreater(mesh.volume,0)
        g=RecordingGeometry();g.group='Detail'
        craft._bamboo_rod(g,P,-2.615,2.615,0,2.625)
        b=g.batches[('Detail','CraftSurfaces')];v=np.asarray(b['v'])
        self.assertGreaterEqual(v[:,0].min(),-2.615);self.assertLessEqual(v[:,0].max(),2.615)
        self.assertLessEqual(abs(v[:,1]).max(),.0175);self.assertLessEqual(abs(v[:,2]-2.625).max(),.0175)

    def test_bamboo_normal_uvs_are_authored_not_repaired(self):
        for idx in range(8):
            g=build(idx,True);g.compact()
            self.assertEqual(g.repair_normal_uvs(),0)

    @unittest.skipUnless(OPTIONS.check_current_native,'Use --check-current-native after a completed export')
    def test_actual_current_native_matches_literal_manifest_flag(self):
        if MANIFEST.get('features',{}).get('shop_personality') is True:
            from shop_personality_contract import validate_native
            ok,detail=validate_native(PROJECT,MANIFEST)
            self.assertTrue(ok,detail)
            return
        from altitude_profile import altitude
        from peer_culling_contract import read_visual,summarize,key
        enabled=MANIFEST.get('features',{}).get('noren_craft') is True
        g=RecordingGeometry()
        for idx,s in enumerate(LAYOUT):
            angle=math.radians(s['front_deg']);n=np.array([math.cos(angle),math.sin(angle),0]);t=np.array([n[1],-n[0],0]);up=np.array([0,0,1]);base=np.array([s['x'],s['y'],s['z']]);axes=[t,n,up]
            g.group='Shops/'+s['id']
            def P(x,y,z):return base+t*x+n*y+up*z
            def B(x,y,z,w,d,h,ma):g.box(P(x,y,z),(w,d,h),ma,axes)
            shopfront.add_shopfront_identity(g,P,B,s['width'],s['depth'],idx,M,staff_entry=True,noren_craft=enabled)
        for b in g.batches.values():
            v=np.asarray(b['v'],float);v[:,2]=altitude(v[:,2]);b['v']=v.tolist()
        g.compact();self.assertEqual(g.repair_normal_uvs(),0);g.bake_mood([])
        expected={k:summarize(dict(group=k[0],material=k[1],vertices=b['v'],uv=b['uv'],colors=np.uint8(b['colors']*255),faces=b['f'])) for k,b in g.batches.items()}
        groups={'Shops/'+s['id']+'/Identity' for s in LAYOUT}
        selected=[b for b in read_visual(PROJECT/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes') if b['group'] in groups]
        selected_keys=[key(b) for b in selected]
        self.assertEqual(len(selected),len(expected),'Unexpected actual native Identity record count')
        self.assertEqual(len(selected_keys),len(set(selected_keys)),'Duplicate actual native Identity (group, material) records')
        actual={key(b):summarize(b) for b in selected}
        self.assertEqual(actual,expected,'Actual native Identity payloads do not match the literal noren_craft feature state')

    def test_preserved_shader_and_texture_dependencies(self):
        # All materials are the existing authored definitions; no global surface
        # shader/normal mapping modification and no synthetic cloth-brightness lift.
        src=inspect.getsource(craft)
        self.assertNotIn('g.material(',src);self.assertNotIn('make_shopfront_atlas',src)
        self.assertNotIn('shader',src.lower().replace('shader,',''))

if __name__=='__main__':
    program=unittest.main(argv=[sys.argv[0]]+UNIT_ARGS,verbosity=2,exit=False)
    result=program.result
    if OPTIONS.report:
        report={'status':'PASS' if result.wasSuccessful() else 'FAIL','testsRun':result.testsRun,
                'failures':[(str(t),detail) for t,detail in result.failures],
                'errors':[(str(t),detail) for t,detail in result.errors],
                'skipped':[(str(t),reason) for t,reason in result.skipped],
                'legacyFixtureSha256':hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
                'checkedCurrentNative':OPTIONS.check_current_native,
                'currentNativeShopReplacement':MANIFEST.get('features',{}).get('shop_personality') is True,
                'historicalNorenGeometryStillTested':True,
                'manifestVersion':MANIFEST.get('version'),
                'literalNorenCraftEnabled':MANIFEST.get('features',{}).get('noren_craft') is True,
                'literalPrintAAEnabled':MANIFEST.get('features',{}).get('shopfront_print_aa') is True,
                'shopfrontSourceSha256':hashlib.sha256(Path(shopfront.__file__).read_bytes()).hexdigest(),
                'norenCraftSourceSha256':hashlib.sha256((HERE/'noren_craft.py').read_bytes()).hexdigest(),
                'scope':'Isolated geometry and optional actual native source export; not Unity/VRChat runtime'}
        OPTIONS.report.parent.mkdir(exist_ok=True,parents=True)
        OPTIONS.report.write_text(json.dumps(report,indent=2))
    raise SystemExit(not result.wasSuccessful())
