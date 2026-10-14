"""Synthetic malicious-mutation proof for the staged exact replacement boundary.

Synthetic rows are NOT accepted design/artifacts. A real after fixture must be
visually reviewed, frozen independently, then exercised via --actual later.
"""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import io
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
# Installed tests resolve their own project only. Staging callers must provide
# a complete private project overlay rather than discovering workspace siblings.
BASE=HERE.parent
import shop_personality_contract as contract

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=contract.load_before();old=set(map(tuple,cls.before['shopKeys']))
        cls.rows=[];shops=[]
        for row in cls.before['rows']:
            value=dict(row)
            if contract.key(row) in old:
                parts=row['group'].split('/');value['group']='/'.join(parts[:2]+['Personality','SyntheticFixture']+parts[2:]);shops.append(value)
            cls.rows.append(value)
        cls.oracle=dict(shopRows=shops,nativeKeyOrder=[list(contract.key(r)) for r in cls.rows])
        cls.manifest=copy.deepcopy(cls.before['manifest']);cls.manifest['features'][contract.FEATURE]=True
        cls.manifest['shopPersonality']=dict(schema=1,version='2.16.0',baselineVersion='2.15.0')
        cls.manifest['version']='2.16.0'
        cls.nonshop=[i for i,r in enumerate(cls.rows) if not r['group'].startswith('Shops/')]
        cls.shop=[i for i,r in enumerate(cls.rows) if r['group'].startswith('Shops/')]
    def check(self,rows=None,manifest=None):
        return contract.validate_summaries(self.rows if rows is None else rows,self.manifest if manifest is None else manifest,oracle=self.oracle,before=self.before)[0]
    def test_baseline_pin_and_exact_partition(self):
        self.assertEqual(len(self.nonshop),815);self.assertEqual(len(self.shop),243)
        self.assertEqual(hashlib.sha256((HERE/'testdata'/contract.BEFORE_NAME).read_bytes()).hexdigest(),contract.BEFORE_SHA256)
    def test_synthetic_unchanged_exact_rows(self):self.assertTrue(self.check())
    def test_each_nonshop_and_shop_rejects_missing_duplicate_mutated_payload(self):
        for i,r in enumerate(self.rows):
            with self.subTest(key=contract.key(r)):
                self.assertFalse(self.check(self.rows[:i]+self.rows[i+1:]))
                self.assertFalse(self.check(self.rows+[r]))
                bad=dict(r,attributesAndIndicesSha256='0'*64)
                self.assertFalse(self.check(self.rows[:i]+[bad]+self.rows[i+1:]))
    def test_actual_counts_are_checked_before_projection(self):
        for field in ('visualMeshCount','visualTriangles'):
            for replacement in (None,True,'1058',-1,0,self.manifest[field]+1):
                m=copy.deepcopy(self.manifest);m[field]=replacement
                ok,detail=contract.validate_summaries(self.rows,m,oracle=self.oracle,before=self.before)
                self.assertFalse(ok);self.assertTrue(any('before projection' in r['reason'] for r in detail['errors']))
    def test_literal_gate_and_version_required(self):
        for flag in (None,False,0,1,'true',{},[]):
            m=copy.deepcopy(self.manifest);m['features'][contract.FEATURE]=flag;self.assertFalse(self.check(manifest=m))
        for name,value in [('schema',True),('schema',2),('version','2.15.0'),('baselineVersion','2.14.0')]:
            m=copy.deepcopy(self.manifest);m['shopPersonality'][name]=value;self.assertFalse(self.check(manifest=m))
        m=copy.deepcopy(self.manifest);del m['features'][contract.FEATURE];self.assertFalse(self.check(manifest=m))
    def test_old_feature_mutation_cannot_hide_behind_new_gate(self):
        for name in self.before['manifest']['features']:
            m=copy.deepcopy(self.manifest);m['features'][name]=False;self.assertFalse(self.check(manifest=m))
    def test_no_shops_prefix_exemption(self):
        for group,material in [('Shops/S01/Personality/Extra','Food_Fake'),('Shops/S09/Personality/Extra','Night_Fake'),('Shops/S01/Unknown','Cedar'),('Tree/Trunk','Food_Fake')]:
            row=dict(self.rows[0],group=group,material=material);m=copy.deepcopy(self.manifest);m['visualMeshCount']+=1;m['visualTriangles']+=row['triangles']
            self.assertFalse(self.check(self.rows+[row],m))
    def test_duplicate_even_with_adjusted_counts(self):
        m=copy.deepcopy(self.manifest);m['visualMeshCount']+=1;m['visualTriangles']+=self.rows[0]['triangles'];self.assertFalse(self.check(self.rows+[self.rows[0]],m))
    def test_order_is_frozen(self):self.assertFalse(self.check(list(reversed(self.rows))))
    def test_unfrozen_after_fail_closed(self):
        if contract.ORACLE_SHA256.startswith('UNFROZEN'):
            with self.assertRaisesRegex(ValueError,'not visually accepted'):contract.load_oracle()
            with self.assertRaisesRegex(ValueError,'not visually accepted'):contract.normalize_summaries(self.rows,self.manifest)
    def test_false_legacy_summary_and_native_positive(self):
        import peer_culling_contract as peer
        m=copy.deepcopy(self.before['manifest']);m['features'][contract.FEATURE]=False
        baseline=peer.load_baseline(BASE)
        with patch.object(contract,'load_oracle',side_effect=AssertionError('Disabled feature must not load after oracle')):
            ok,detail=peer.validate_summaries(self.before['rows'],m,baseline)
            self.assertTrue(ok,detail)
            # Reconstruct a TEST-ONLY exact legacy native using the project's
            # unchanged nonshop arrays plus immutable old shop arrays. This is
            # not admission of the current shops, and never loads the after art
            # oracle. The whole serialized native must match the frozen SHA.
            import numpy as np
            import shop_personality_test_fixture as inverse
            from visual_optimization_test_fixture import native_sha
            native=BASE/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'
            actual={contract.key(b):b for b in peer.read_visual(native)}
            raw=(HERE/'testdata'/inverse.INVERSE_NAME).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),inverse.INVERSE_SHA256)
            with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
                for i,pair in enumerate(self.before['shopKeys']):
                    k=tuple(pair);b={'group':k[0],'material':k[1]}
                    for attr in ('vertices','uv','colors','faces'):b[attr]=archive[str(i)+'_'+attr].copy()
                    actual[k]=b
            batches=[actual[contract.key(r)] for r in self.before['rows']]
            self.assertEqual(native_sha(batches),contract.BEFORE_NATIVE_SHA256)
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'Source').symlink_to(HERE,target_is_directory=True)
                (root/'Docs').mkdir();(root/'Docs/baselines').symlink_to(BASE/'Docs/baselines',target_is_directory=True)
                assets=root/'Assets/TreeTopYokocho';assets.mkdir(parents=True)
                (assets/'Shaders').symlink_to(BASE/'Assets/TreeTopYokocho/Shaders',target_is_directory=True)
                # This fixture represents the pre-shop runtime too, not the
                # current RPG builder/helper paired with an old global profile.
                # Restore only independently pinned old Editor files; never
                # edit the live runtime or weaken its new source guard.
                for rel,expected_sha in self.before['dependencies'].items():
                    if not rel.startswith('Assets/TreeTopYokocho/Editor/'):continue
                    source=BASE/rel
                    archived=HERE/'testdata/rpg_identity_legacy_builder_2_16.cs'
                    if rel.endswith('/YokochoWorldBuilder.cs') and archived.is_file():source=archived
                    content=source.read_bytes()
                    self.assertEqual(hashlib.sha256(content).hexdigest(),expected_sha)
                    destination=root/rel;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
                data=assets/'Data';data.mkdir()
                profile=(HERE/'testdata/shop_profile_before_2_15.json').read_bytes()
                import shop_profile_contract as profile_contract
                self.assertEqual(hashlib.sha256(profile).hexdigest(),profile_contract.OLD_PROFILE_SHA256)
                (data/'FantasyMaterials.json').write_bytes(profile)
                legacy=data/'VisualMeshes.bytes'
                with legacy.open('wb') as stream:
                    stream.write(b'JYWM'+struct.pack('<II',1,len(batches)))
                    for batch in batches:
                        for name in ('group','material'):
                            encoded=batch[name].encode();stream.write(struct.pack('<I',len(encoded))+encoded)
                        stream.write(struct.pack('<II',len(batch['vertices']),batch['faces'].size))
                        stream.write(peer.raw_attributes(batch))
                self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(),contract.BEFORE_NATIVE_SHA256)
                ok,detail=peer.validate_peer_culling(root,m,legacy);self.assertTrue(ok,detail)
        bad=copy.deepcopy(self.manifest);bad['features'][contract.FEATURE]=False
        rows,m,errors,detail=contract.normalize_summaries(self.rows,bad);self.assertTrue(errors)
    def test_summary_projection_authenticates_metadata_before_overwrite(self):
        m=copy.deepcopy(self.manifest)
        oracle=dict(self.oracle,manifestFieldHashes={k:contract.digest(v) for k,v in m.items()})
        def corrupted(path,value):
            out=copy.deepcopy(m);node=out
            for key in path[:-1]:node=node[key]
            node[path[-1]]=value;return out
        mutations=[(['meshOptimization','cityCaps','builderSha256'],'0'*64),(['meshOptimization','sea','waterShaderSha256'],'0'*64),(['stations',0,'exit'],[0,0,0]),(['lights',0,'range'],999)]
        with patch.object(contract,'load_oracle',return_value=oracle),patch.object(contract,'audit_metadata',return_value=(True,{'errors':[]})):
            for path,value in mutations:
                bad=corrupted(path,value);rows,projected,errors,detail=contract.normalize_summaries(self.rows,bad)
                self.assertTrue(errors,path);self.assertIs(rows,self.rows);self.assertIs(projected,bad)

    def test_local_world_route_coordinate_and_descriptor_boundary(self):
        import numpy as np
        P=lambda p:np.asarray(p)+[10,20,100]
        local={'name':'staff','role':'staff','points':[[0,0,0],[1,1,0]],'centerline':[[0,0],[1,1]],'servicePoint':[1,1,0],'requiredRadius':.325}
        world={k:copy.deepcopy(v) for k,v in local.items() if k!='centerline'}
        world['points']=[P(p).tolist() for p in local['points']];world['servicePoint']=P(local['servicePoint']).tolist()
        errors=[];contract._audit_route_transform(local,world,P,'test',errors);self.assertEqual(errors,[])
        for field,value in [('points',local['points']),('servicePoint',local['servicePoint']),('role','customer'),('requiredRadius',.25),('centerline',local['centerline'])]:
            bad=copy.deepcopy(world);bad[field]=value;errors=[];contract._audit_route_transform(local,bad,P,'test',errors);self.assertTrue(errors,field)
        bad=copy.deepcopy(world);del bad['servicePoint'];errors=[];contract._audit_route_transform(local,bad,P,'test',errors);self.assertTrue(errors)

    def test_glb_scene_placement_and_unique_triangle_roster(self):
        from pygltflib import GLTF2,Scene,Node,Mesh,Primitive,Material
        from audit_shop_personality_glb import identity_scene_errors
        gl=GLTF2(scene=0,scenes=[Scene(nodes=[0])],nodes=[Node(mesh=0,name='Tree')],meshes=[Mesh(name='Tree',primitives=[Primitive(mode=4)])])
        self.assertEqual(identity_scene_errors(gl,'synthetic'),[])
        for target,field,value in [('node','translation',[1,0,0]),('node','scale',[2,2,2]),('node','rotation',[0,0,1,0]),('node','children',[0]),('node','mesh',1),('scene','nodes',[]),('primitive','mode',1)]:
            bad=copy.deepcopy(gl);obj={'node':bad.nodes[0],'scene':bad.scenes[0],'primitive':bad.meshes[0].primitives[0]}[target];setattr(obj,field,value)
            self.assertTrue(identity_scene_errors(bad,'synthetic'),(target,field))
        bad=copy.deepcopy(gl);bad.meshes.append(copy.deepcopy(bad.meshes[0]));bad.nodes.append(Node(mesh=1,name='Tree'));bad.scenes[0].nodes=[0,1]
        self.assertTrue(identity_scene_errors(bad,'synthetic'))
        bad=copy.deepcopy(gl);bad.materials=[Material(name='Cedar'),Material(name='Cedar')];self.assertTrue(identity_scene_errors(bad,'synthetic'))

    def test_frozen_glb_exact_bytes_and_literal_gate(self):
        from audit_shop_personality_glb import audit_frozen
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'Assets/TreeTopYokocho/Data';data.mkdir(parents=True);(root/'Source').mkdir()
            path=root/'Source/TreeTopYokocho.glb';path.write_bytes(b'SYNTHETIC TEST ONLY, NOT APPROVED ART')
            manifest={'features':{contract.FEATURE:True}};mp=data/'WorldManifest.json';mp.write_text(json.dumps(manifest))
            oracle={'approvedGlbSha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            with patch.object(contract,'load_oracle',return_value=oracle):
                self.assertEqual(audit_frozen(root)['status'],'PASS')
                path.write_bytes(path.read_bytes()+b'changed');self.assertEqual(audit_frozen(root)['status'],'FAIL')
            for value in (False,1,'true'):
                manifest['features'][contract.FEATURE]=value;mp.write_text(json.dumps(manifest))
                with patch.object(contract,'load_oracle',side_effect=AssertionError('Invalid gate must not load art oracle')):
                    self.assertEqual(audit_frozen(root)['status'],'FAIL')

    def test_no_native_inverse_import_in_production(self):
        source=(HERE/'shop_personality_contract.py').read_text()
        self.assertNotIn('import shop_personality_test_fixture',source)
        self.assertNotIn('restore_prior_shops',source)
    def test_metadata_without_gate_is_rejected(self):
        rows,m,errors,detail=contract.normalize_summaries([],{ 'shopPersonality':{} })
        self.assertTrue(errors)

if __name__=='__main__':unittest.main(verbosity=2)
