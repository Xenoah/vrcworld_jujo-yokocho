"""Self-contained, independent noren payload oracle and adversarial suite.

All feature matrices and optional isolated after insertion are SYNTHETIC, never
an integrated-world claim. No authoring, generation, rendering or file refresh.
"""
import argparse
import copy
import hashlib
import itertools
import json
import struct
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode = True
import numpy as np
import peer_culling_contract as c
import noren_payload_contract as n

ORACLE_SHA = '0dc276edda30ca4f09fe94a8329ced4f0388dc5f2d9a4e9efde0e6b0470d381a'
BASELINE_SHA = 'ccb5845dd0c3dd1dd9bdecb2bdd1ce5d32e8d8d501de196af7a5a6733129b26e'
NATIVE_SHA = 'ccf84f6801513e5768a63666e9dc465982614dad9e525c4237ce879a19f9c8ff'
SOURCE_SHA = '305c179d5ff632770becdb3f43335b22e28330feb3381763ba32a250d216adf6'
PEER_SHA = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
FIELDS = ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256')
OLD_KEYS = {(f'Shops/S{i:02}/Identity', m) for i in range(1,9) for m in
            ('Cedar','Counter','DarkTimber','Iron','ShopfrontInkWood','ShopfrontTextile','ShopfrontWashi')}
ADDED = {(f'Shops/S{i:02}/Identity','CraftSurfaces') for i in range(1,9)}
REMOVED = {(f'Shops/S{i:02}/Identity','Counter') for i in (1,2,4,6,7)}
UNCHANGED = {(f'Shops/S{i:02}/Identity',m) for i in range(1,9)
             for m in ('Cedar','Iron','ShopfrontInkWood','ShopfrontWashi')}
FALSE_FLAGS = (None, False, 0, 1, 1.0, 'true', 'True', 'false', {}, [], np.bool_(True))


def oracle():
    raw = (Path(__file__).parent/'testdata/noren_contract_oracle.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORACLE_SHA:
        raise ValueError('Independent noren test oracle file hash changed')
    return json.loads(raw)


def historical_identity_fixture(rows, manifest):
    """Explicit synthetic historical Identity normalization for older matrices."""
    old = oracle()['original']
    result = [dict(r) for r in rows if c.key(r) not in OLD_KEYS | ADDED]
    result += copy.deepcopy(old)
    m = copy.deepcopy(manifest)
    m.setdefault('features', {})['noren_craft'] = False
    return result, counted(result, m)


def counted(rows, manifest):
    return dict(manifest, visualMeshCount=len(rows), visualTriangles=sum(r['triangles'] for r in rows))


def rejects(result, reasons, pair=None):
    ok, d = result
    errors = d.get('errors', [])
    return (not ok and bool(errors) and {e.get('reason') for e in errors} == set(reasons)
            and (pair is None or any(e.get('key') == pair or pair in e.get('keys', []) for e in errors)))


def raises(fn, message):
    try:
        fn()
    except (ValueError, OSError) as error:
        return str(error) == message
    return False


def serialized(batches):
    out = bytearray(b'JYWM'+struct.pack('<II',1,len(batches)))
    for b in batches:
        for name in ('group','material'):
            value=b[name].encode();out.extend(struct.pack('<I',len(value))+value)
        out.extend(struct.pack('<II',len(b['vertices']),3*len(b['faces'])))
        for name,dtype in (('vertices','<f4'),('uv','<f4'),('colors','u1'),('faces','<u4')):
            out.extend(np.asarray(b[name],dtype=dtype).tobytes())
    return bytes(out)


def run_noren_cases(current_rows, current_manifest, baseline, tests, *, batches=None,
                    root=None, noren_candidate_batches=None):
    from test_cloud_depth_contract import BEFORE as CLOUD_BEFORE, AFTER as CLOUD_AFTER
    from test_scenery_revision_contract import SNOW_HASHES, STAGE_ADDED, STAGE_APPROVED, STAGE_ORIGINAL
    from test_herb_planter_roster_contract import ADDED as HERBS, REMOVED as PLANTS, ROOFS
    data=oracle();old={c.key(r):r for r in data['original']};after={c.key(r):r for r in data['after']}
    original_protected={c.key(r):r for r in baseline['protectedGroups']}
    protected=(set(original_protected)-set(c.OLD_KEYS))|set(c.NEW_TO_OLD)
    current={c.key(r):r for r in current_rows}
    template=next(r for r in current_rows if c.key(r) not in protected|OLD_KEYS|ADDED|STAGE_ORIGINAL)
    check=lambda rows,m: c.validate_summaries(rows,counted(rows,m),baseline)
    payload_tuple=lambda r:tuple(r[f] for f in ('group','material')+FIELDS)
    tests.expect('noren_independent_pins','independent exact original56 and approved59 literal rows',lambda:
        tuple(map(payload_tuple,data['original']))==n.ORIGINAL_PAYLOADS
        and tuple(map(payload_tuple,data['after']))==n.APPROVED_PAYLOADS
        and set(old)==OLD_KEYS and set(after)==(OLD_KEYS-REMOVED)|ADDED
        and {k for k in old.keys()&after.keys() if old[k]==after[k]}==UNCHANGED)
    slice_fields=('group','material','component','vertexStart','triangleStart','vertexCount','triangleCount',
                  'geometrySha256','attributesAndIndicesSha256','afterVertexStart','afterTriangleStart')
    tests.expect('noren_independent_pins','107 independently archived old/new exact slice descriptors',lambda:
        tuple(tuple(r[f] for f in slice_fields) for r in data['slices'])==n.PRESERVED_SLICES)
    tests.expect('noren_independent_pins','baseline and approved isolated source/native pins fixed independently',lambda:
        n.BASELINE_SHA256==BASELINE_SHA and n.APPROVED_NATIVE_SHA256==NATIVE_SHA
        and n.APPROVED_SOURCE_SHA256==SOURCE_SHA and c.BASELINE_FILE_SHA256==PEER_SHA)
    tests.expect('noren_independent_pins','original56 are unprotected by peer payload baseline',lambda:
        OLD_KEYS<={tuple(k) for k in baseline['unprotectedBatchKeys']} and not OLD_KEYS&protected
        and not ADDED&({tuple(k) for k in baseline['unprotectedBatchKeys']}|protected))
    base=[]
    for pair in sorted(protected|{tuple(k) for k in baseline['unprotectedBatchKeys']}):
        row=dict(old.get(pair,current.get(pair,dict(template,group=pair[0],material=pair[1]))))
        if pair in CLOUD_BEFORE or pair in SNOW_HASHES:row=dict(original_protected[pair])
        base.append(row)
    def fixture(surface=False,herbs=False,snow=False,stage=False,cloud=False,noren=False):
        rows=[dict(r) for r in base if not (herbs and c.key(r) in PLANTS)
              and not (noren and c.key(r) in OLD_KEYS)]
        added=(ROOFS if surface else set())|(HERBS if herbs else set())|(STAGE_ADDED if stage else set())
        for pair in sorted(added):
            rows.append(dict(group=pair[0],material=pair[1],**STAGE_APPROVED[pair]) if pair in STAGE_APPROVED
                        else dict(current.get(pair,dict(template,group=pair[0],material=pair[1]))))
        if noren:rows+=copy.deepcopy(data['after'])
        for i,r in enumerate(rows):
            pair=c.key(r)
            if snow and pair in SNOW_HASHES:rows[i]=dict(r,attributesAndIndicesSha256=SNOW_HASHES[pair][1])
            if cloud and pair in CLOUD_AFTER:rows[i]=dict(CLOUD_AFTER[pair])
        m=copy.deepcopy(current_manifest)
        m['features']=dict(peer_culling_split=True,surface_refinement=surface,herb_planters=herbs,
                           snow_deposition=snow,stage_roof_craft=stage,cloud_depth=cloud,noren_craft=noren)
        return rows,m
    for flags in itertools.product((False,True),repeat=6):
        rows,m=fixture(*flags);ok,d=check(rows,m);surface,herbs,snow,stage,cloud,noren=flags
        tests.expect('noren_synthetic_64_matrix','SYNTHETIC six literal feature gates '+repr(flags),lambda:
            ok and d['expectedTotalBatches']==d['actualTotalBatches']==1051+8*surface-8*herbs+4*stage+3*noren
            and d['actualProtectedBatches']==d['expectedProtectedBatches']==603
            and d['unchangedProtectedBatches']==595-8*snow-8*cloud
            and d['unchangedProtectedGeometryBatches']==595-8*cloud
            and d['colorRevisedProtectedBatches']==8*snow and d['geometryRevisedProtectedBatches']==8*cloud
            and d['exactPeerSplitProtectedBatches']==8 and d['separatelyPinnedOriginalStageBatches']==15*stage
            and d['separatelyPinnedStageRoofCraftBatches']==4*stage and d['exactStageRoofCraftPayloadBatches']==4*stage
            and d['norenCraft'] is noren and d['originalIdentityProvenanceBatches']==56*noren
            and d['separatelyPinnedNorenIdentityBatches']==d['exactNorenIdentityPayloadBatches']==59*noren
            and d['unchangedNorenIdentityBatches']==32*noren and d['revisedNorenIdentityBatches']==19*noren
            and d['addedNorenIdentityBatches']==8*noren and d['removedNorenIdentityBatches']==5*noren
            and d['expectedPreservedNorenComponentSlices']==107*noren
            and d['exactPreservedNorenComponentSlices'] is None)
    rows,m=fixture(True,True,True,True,True,True);before,bm=fixture(True,True,True,True,True,False)
    idx={c.key(r):i for i,r in enumerate(rows)}
    payload_reason={'Approved noren Identity payload changed'}
    for flag in FALSE_FLAGS:
        changed=copy.deepcopy(m);changed['features']['noren_craft']=flag
        tests.expect('noren_literal_gate','nonliteral old path '+repr(flag),lambda changed=changed:check(before,changed))
        tests.expect('noren_literal_gate','nonliteral rejects after '+repr(flag),lambda changed=changed:
            rejects(check(rows,changed),{'Missing batches','Extra/unapproved batches'}))
    changed=copy.deepcopy(m);del changed['features']['noren_craft']
    tests.expect('noren_literal_gate','omitted flag preserves legacy',lambda:check(before,changed))
    tests.expect('noren_literal_gate','omitted flag rejects crafted roster',lambda:
        rejects(check(rows,changed),{'Missing batches','Extra/unapproved batches'}))
    tests.expect('noren_literal_gate','true rejects original payloads/roster',lambda:
        rejects(check(before,m),{'Missing batches','Extra/unapproved batches','Approved noren Identity payload changed'}))
    for flags in (None,False,1,'true',[],np.bool_(True)):
        r,z=fixture();z['features']=flags
        tests.expect('noren_literal_gate','invalid feature container is disabled '+repr(flags),lambda z=z:
            rejects(check(r,z),{'features.peer_culling_split must be literal true'}))
    for pair,row in after.items():
        index=idx[pair]
        tests.expect('noren_exact_roster',str(pair)+' missing recounted',lambda index=index,pair=pair:
            rejects(check(rows[:index]+rows[index+1:],m),{'Missing batches'},pair))
        tests.expect('noren_exact_roster',str(pair)+' duplicate recounted',lambda row=row,pair=pair:
            rejects(check(rows+[row],m),{'Duplicate batches'},pair))
        for field,value in [('group',row['group']+'/Cell_0_0'),('group',row['group']+'/Far'),
                            ('group',row['group'].lower()),('group','Shops/S09/Identity'),
                            ('group',row['group']+'Extra'),('material',row['material']+'Extra')]:
            changed=dict(row,**{field:value})
            tests.expect('noren_exact_roster',str(pair)+' alias '+str(c.key(changed)),lambda index=index,changed=changed,pair=pair:
                rejects(check(rows[:index]+[changed]+rows[index+1:],m),{'Missing batches','Extra/unapproved batches'},pair))
        for field in FIELDS:
            for value in ((-1,row[field]+1) if field in ('vertices','triangles') else (None,'','0'*64,'f'*64)):
                changed=dict(row,**{field:value})
                tests.expect('noren_exact_payload',str(pair)+' wrong '+field+' '+repr(value),lambda index=index,changed=changed,pair=pair:
                    rejects(check(rows[:index]+[changed]+rows[index+1:],m),payload_reason,pair))
            if field not in ('vertices','triangles'):
                changed=dict(row);del changed[field]
                tests.expect('noren_exact_payload',str(pair)+' missing '+field,lambda index=index,changed=changed,pair=pair:
                    rejects(check(rows[:index]+[changed]+rows[index+1:],m),payload_reason,pair))
    for pair in REMOVED:
        tests.expect('noren_counter_roster',str(pair)+' obsolete Counter retained',lambda pair=pair:
            rejects(check(rows+[old[pair]],m),{'Extra/unapproved batches'},pair))
    for pair in {(f'Shops/S{i:02}/Identity','Counter') for i in (3,5,8)}:
        tests.expect('noren_counter_roster',str(pair)+' retained cap is exactly96 vertices44 triangles',lambda pair=pair:
            after[pair]['vertices']==96 and after[pair]['triangles']==44)
    missing_pair=sorted(ADDED)[0];dup_pair=sorted(ADDED)[1]
    tests.expect('noren_exact_roster','duplicate cannot hide missing same total',lambda:
        rejects(check([r for r in rows if c.key(r)!=missing_pair]+[after[dup_pair]],m),{'Missing batches','Duplicate batches'}))
    tests.expect('noren_exact_roster','batch order itself does not matter',lambda:check(list(reversed(rows)),m))
    for pair in (OLD_KEYS&set(after))-UNCHANGED:
        index=idx[pair]
        tests.expect('noren_stale_payload',str(pair)+' original/prototype payload is not approved',lambda index=index,pair=pair:
            rejects(check(rows[:index]+[old[pair]]+rows[index+1:],m),payload_reason,pair))
    # Deliberately preserve legacy historical policy: the new56 requirements are
    # never silently applied while false, and module/baseline availability is irrelevant.
    with patch.object(n,'load_baseline',side_effect=AssertionError('false path must not load Identity baseline')):
        tests.expect('noren_false_compatibility','false summary path retains original policy',lambda:check(before,bm))
        if root is not None and not n.enabled(current_manifest):
            tests.expect('noren_false_compatibility','actual adapter false does not load new baseline',lambda:
                c.validate_peer_culling(root,current_manifest))
    with patch.dict(sys.modules,{'noren_payload_contract':None}):
        tests.expect('noren_false_compatibility','disabled summary never imports new module',lambda:check(before,bm))
    with patch.dict(sys.modules, {'noren_payload_contract': None}):
        tests.expect('noren_baseline_admission', 'true missing helper is structured input failure', lambda:
            c.validate_summaries(rows, counted(rows, m), baseline) ==
            (False, {'reason': 'Invalid peer-culling input', 'error': 'Missing noren payload contract module'}))
    for name, mode in (('APPROVED_PAYLOADS', 'count'), ('APPROVED_PAYLOADS', 'hash'),
                       ('APPROVED_PAYLOADS', 'duplicate'), ('PRESERVED_SLICES', 'short'),
                       ('PRESERVED_SLICES', 'duplicate'), ('PRESERVED_SLICES', 'offset')):
        altered = list(getattr(n, name))
        row = list(altered[0])
        if mode == 'count': row[2] += 1
        elif mode == 'hash': row[4] = '0'*64
        elif mode == 'short': row = row[:-1]
        elif mode == 'offset': row[-2] += 1
        elif mode == 'duplicate': altered[1] = altered[0]
        altered[0] = tuple(row)
        with patch.object(n, name, tuple(altered)):
            tests.expect('noren_production_schema', name+' '+mode+' fails with exact schema error', lambda:
                raises(lambda: n.validate_schema(baseline), 'Invalid explicit noren Identity revision schema'))
    baseline_path=Path(__file__).resolve().parents[1]/'Docs/baselines'/n.BASELINE_NAME
    raw=baseline_path.read_bytes()
    tests.expect('noren_baseline_admission','original-only file fixed SHA',lambda:hashlib.sha256(raw).hexdigest()==BASELINE_SHA)
    with patch.object(Path,'read_bytes',return_value=raw):
        tests.expect('noren_baseline_admission','original baseline code/file schema exact',lambda:bool(n.load_baseline('/unused')))
    for label,contents,message in [('tampered',raw+b' ', 'Frozen v2.11 original-Identity baseline file hash changed')]:
        with patch.object(Path,'read_bytes',return_value=contents):
            tests.expect('noren_baseline_admission',label,lambda:raises(lambda:n.load_baseline('/unused'),message))
    with patch.object(Path,'read_bytes',side_effect=FileNotFoundError('missing')):
        tests.expect('noren_baseline_admission','missing exact diagnostic',lambda:
            raises(lambda:n.load_baseline('/unused'),'Missing frozen v2.11 original-Identity baseline file'))
    for mutation in ('schema','duplicate','count','missing','slice_duplicate','slice_hash'):
        broken=json.loads(raw)
        if mutation=='schema':broken['schemaVersion']=2
        elif mutation=='duplicate':broken['originalIdentityGroups'][1]=broken['originalIdentityGroups'][0]
        elif mutation=='count':broken['originalIdentityGroups'][0]['vertices']+=1
        elif mutation=='missing':del broken['originalIdentityGroups']
        elif mutation=='slice_duplicate':broken['originalPreservedComponents'][1]=broken['originalPreservedComponents'][0]
        else:broken['originalPreservedComponents'][0]['attributesAndIndicesSha256']='0'*64
        br=json.dumps(broken).encode()
        # Bypass only outer file integrity to independently exercise schema check.
        with patch.object(Path,'read_bytes',return_value=br),patch.object(n,'BASELINE_SHA256',hashlib.sha256(br).hexdigest()):
            expected='Invalid frozen original-Identity baseline schema' if mutation=='missing' else 'Original-Identity code pins differ from frozen archive baseline'
            tests.expect('noren_baseline_schema',mutation+' rejected after controlled outer-pin bypass',lambda expected=expected:
                raises(lambda:n.load_baseline('/unused'),expected))
    with patch.object(Path,'read_bytes',return_value=raw),patch.object(n,'ORIGINAL_PAYLOADS',n.ORIGINAL_PAYLOADS[:-1]):
        tests.expect('noren_baseline_schema','code pins cannot omit original row',lambda:
            raises(lambda:n.load_baseline('/unused'),'Original-Identity code pins differ from frozen archive baseline'))
    # Current false export is independently compared to original archive here;
    # this assertion deliberately does not alter the historical production policy.
    if batches is not None:
        actual_identity=[b for b in batches if c.key(b) in OLD_KEYS|ADDED]
        expected=after if n.enabled(current_manifest) else old
        tests.expect('noren_actual_native','current literal state exact Identity payloads',lambda:
            len(actual_identity)==len(expected) and {c.key(b) for b in actual_identity}==set(expected)
            and len({c.key(b) for b in actual_identity})==len(actual_identity)
            and all(c.summarize(b)==expected[c.key(b)] for b in actual_identity))
    native=noren_candidate_batches if noren_candidate_batches is not None else (
        [b for b in batches if c.key(b) in after] if batches is not None and n.enabled(current_manifest) else None)
    if native is not None:
        run_native_cases(native,rows,m,baseline,tests,data,root)


def run_native_cases(native,rows,manifest,baseline,tests,data,root):
    """Real native arrays: all59 full rows and all107 explicitly located slices."""
    expected={c.key(r):r for r in data['after']};idx={c.key(r):i for i,r in enumerate(rows)}
    tests.expect('noren_isolated_native','real59 native rows equal independent accepted oracle',lambda:
        len(native)==59 and len({c.key(b) for b in native})==59
        and all(c.summarize(b)==expected.get(c.key(b)) for b in native))
    tests.expect('noren_isolated_native','all107 original component slices exact after index rebasing',lambda:
        n.validate_native_slices(native)[0] and n.validate_native_slices(native)[1]['exactPreservedNorenComponentSlices']==107)
    for original in native:
        pair=c.key(original);index=idx[pair]
        for mutation in ('x','y','z','u','v','r','g','b','alpha','index','winding','vertex_order','face_order'):
            b=dict(original);b.update({f:original[f].copy() for f in ('vertices','uv','colors','faces')})
            if mutation in ('x','y','z','u','v'):
                field='vertices' if mutation in ('x','y','z') else 'uv';axis=('x','y','z').index(mutation) if field=='vertices' else ('u','v').index(mutation)
                b[field][0,axis]=np.nextafter(b[field][0,axis],np.float32(np.inf))
            elif mutation in ('r','g','b','alpha'):b['colors'][0,('r','g','b','alpha').index(mutation)]^=1
            elif mutation=='index':b['faces'][0,0]=(int(b['faces'][0,0])+1)%len(b['vertices'])
            elif mutation=='winding':b['faces'][0]=b['faces'][0,[0,2,1]]
            elif mutation=='face_order':b['faces'][[0,-1]]=b['faces'][[-1,0]]
            else:
                for f in ('vertices','uv','colors'):b[f][[0,-1]]=b[f][[-1,0]]
                f=b['faces'].copy();b['faces'][f==0]=len(b['vertices'])-1;b['faces'][f==len(b['vertices'])-1]=0
            changed=rows[:index]+[c.summarize(b)]+rows[index+1:]
            tests.expect('noren_real_array_mutations',str(pair)+' '+mutation,lambda changed=changed,pair=pair:
                rejects(c.validate_summaries(changed,counted(changed,manifest),baseline),{'Approved noren Identity payload changed'},pair))
    mapping={c.key(b):i for i,b in enumerate(native)}
    for slice_row in data['slices']:
        pair=c.key(slice_row);component=(pair[0],pair[1],slice_row['component']);index=mapping[pair]
        original=native[index]
        for mode in ('position','uv','alpha','cross_span','winding'):
            b=dict(original);b.update({f:original[f].copy() for f in ('vertices','uv','colors','faces')})
            vs=slice_row['afterVertexStart'];fs=slice_row['afterTriangleStart']
            if mode=='position':b['vertices'][vs,0]=np.nextafter(b['vertices'][vs,0],np.float32(np.inf))
            elif mode=='uv':b['uv'][vs,1]=np.nextafter(b['uv'][vs,1],np.float32(np.inf))
            elif mode=='alpha':b['colors'][vs,3]^=1
            elif mode=='cross_span':b['faces'][fs,0]=vs+slice_row['vertexCount']
            else:b['faces'][fs]=b['faces'][fs,[0,2,1]]
            changed=native[:index]+[b]+native[index+1:];ok,d=n.validate_native_slices(changed)
            reason='Preserved noren component indices cross vertex span' if mode=='cross_span' else 'Preserved noren component payload changed'
            tests.expect('noren_preserved107_mutations',str(component)+' '+mode,lambda ok=ok,d=d,component=component,reason=reason:
                not ok and any(e['component']==component and e['reason']==reason for e in d['errors']))
    for mode in ('offset','name','duplicate','rebase'):
        changed=list(n.PRESERVED_SLICES);r=list(changed[0])
        if mode=='offset':r[9]+=1
        elif mode=='name':r[2]+='Renamed'
        elif mode=='duplicate':changed[1]=changed[0]
        else:r[10]+=1
        changed[0]=tuple(r)
        with patch.object(n,'PRESERVED_SLICES',tuple(changed)):
            if mode in ('offset','rebase'):
                tests.expect('noren_slice_schema',mode+' explicit range fails',lambda:not n.validate_native_slices(native)[0])
            else:
                # Baseline admission covers descriptor identity, not only bytes.
                raw=(Path(__file__).resolve().parents[1]/'Docs/baselines'/n.BASELINE_NAME).read_bytes()
                with patch.object(Path,'read_bytes',return_value=raw):
                    tests.expect('noren_slice_schema',mode+' descriptor baseline mismatch',lambda:
                        raises(lambda:n.load_baseline('/unused'),'Original-Identity code pins differ from frozen archive baseline'))
    with tempfile.TemporaryDirectory(prefix='noren-native-') as td:
        file=Path(td)/'bad.bytes'
        for mode in ('nonfinite_xyz','nonfinite_uv','index_bounds','trailing','truncated'):
            b=dict(native[0]);b.update({f:native[0][f].copy() for f in ('vertices','uv','colors','faces')})
            if mode=='nonfinite_xyz':b['vertices'][0,1]=np.nan
            elif mode=='nonfinite_uv':b['uv'][0,0]=np.inf
            elif mode=='index_bounds':b['faces'][0,0]=len(b['vertices'])
            raw=serialized([b])
            if mode=='trailing':raw+=b'X'
            elif mode=='truncated':raw=raw[:-1]
            file.write_bytes(raw)
            def fails():
                try:c.read_visual(file)
                except ValueError as e:
                    text=str(e)
                    return text==('Unexpected trailing JYWM bytes' if mode=='trailing' else
                                  'Declared JYWM field exceeds remaining payload' if mode=='truncated' else
                                  'Nonfinite attributes or out-of-range indices')
                return False
            tests.expect('noren_native_reader',mode+' exact diagnostic',fails)
    if root is not None:
        # Adapter explicitly receives synthetic all-world input by mocks; no
        # generated fixture is passed off as the actual exported world.
        raw=(Path(__file__).resolve().parents[1]/'Docs/baselines'/n.BASELINE_NAME).read_bytes()
        other=[dict(group=r['group'],material=r['material'],_summary=r) for r in rows if c.key(r) not in expected]
        full=other+native;real_summarize=c.summarize
        summary=lambda b:b['_summary'] if '_summary' in b else real_summarize(b)
        with patch.object(c,'read_visual',return_value=full),patch.object(c,'summarize',side_effect=summary),patch.object(n,'load_baseline',return_value=json.loads(raw)):
            tests.expect('noren_synthetic_adapter','synthetic fullworld insertion passes full adapter107 slice checks',lambda:
                c.validate_peer_culling(root,counted(rows,manifest)))
        for error in ('Missing frozen v2.11 original-Identity baseline file','Frozen v2.11 original-Identity baseline file hash changed'):
            with patch.object(n,'load_baseline',side_effect=ValueError(error)):
                result=c.validate_peer_culling(root,counted(rows,manifest))
                tests.expect('noren_synthetic_adapter','true missing/wrong baseline exact adapter diagnostic '+error,lambda result=result,error=error:
                    result==(False,{'reason':'Invalid peer-culling input','error':error}))


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--noren-candidate',type=Path,help='Optional approved isolated after fixture; SYNTHETIC insertion only')
    args=p.parse_args();from test_peer_culling_contract import Tests
    tests=Tests();manifest={}
    try:
        manifest=json.loads((args.root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
        batches=c.read_visual(args.root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes');rows=list(map(c.summarize,batches))
        tests.expect('actual_export','only current exported world with actual literal features',lambda:c.validate_peer_culling(args.root,manifest))
        candidate=c.read_visual(args.noren_candidate) if args.noren_candidate else None
        if args.noren_candidate:tests.expect('noren_isolated_native','optional candidate file SHA is authoritative',lambda:
            hashlib.sha256(args.noren_candidate.read_bytes()).hexdigest()==NATIVE_SHA)
        run_noren_cases(rows,manifest,c.load_baseline(args.root),tests,batches=batches,root=args.root,noren_candidate_batches=candidate)
    except Exception as e:tests.failures.append(dict(test='suite setup',error=str(e),exception=type(e).__name__))
    result=dict(status='FAIL' if tests.failures else 'PASS',count=tests.count,categories=tests.categories,failures=tests.failures,
                actualFeatures=manifest.get('features'),isolatedCandidateSupplied=bool(args.noren_candidate),
                scope='Actual current export plus SYNTHETIC 64-feature matrix and optional ISOLATED noren after arrays. No future integrated-world acceptance or runtime claim.')
    result['approvedIsolatedNativeSha256'] = NATIVE_SHA
    result['approvedSourceSha256'] = SOURCE_SHA
    result['actualNativeSha256'] = hashlib.sha256((args.root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes()).hexdigest()
    if manifest.get('testFixtureScope'):
        result['scope'] = manifest['testFixtureScope'] + '; ' + result['scope']
    if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return bool(tests.failures)


if __name__=='__main__':raise SystemExit(main())
