"""Exact additive v2.19 signs above immutable accepted v2.18 geometry.

No production geometry inverse, broad shop exemption, or art self-approval.
Current bytes and metadata authenticate before any historical projection.
"""
import copy,gzip,hashlib,json
from pathlib import Path

VERSION='2.19.0'
FEATURE='venue_projecting_signs'
METADATA='venueProjectingSigns'
BEFORE_NATIVE_SHA256='d0386d484fc9de77ee43d41db4a36aab916027bc81091ad573afca13a0fc69db'
BEFORE_GLB_SHA256='f0c2313043ec2fdaeda99a80d516ef592a01b5b5cdfc35d34c02c5eb3bafc32f'
BEFORE_ORACLE_SHA256='50bf06fbc5f6d85b00e841c7d166cad167682367d1a3908e612d959913993a0d'
BEFORE_NAME='projecting_sign_before_2_18.json.gz'
BEFORE_SHA256='c55ca3b8eb818ae553321f28c90d7446df166050cf44867ecac41db78aafff91'
ORACLE_NAME='projecting_sign_after_2_19.json.gz'
ORACLE_SHA256='c6f9ba4cacfd706382376ec7d6084187eca5933b331621db3d0afa159f259366'
SOURCE_CHANGES=('Source/build_world.py',)
NEW_SOURCES=('Source/venue_projecting_signs.py',)
FIELDS=('group','material','vertices','triangles','geometrySha256','attributesAndIndicesSha256')
KEYS=(('Shops/S01/ProjectingSigns/DragonEmberAssembly', 'Iron'),
 ('Shops/S01/ProjectingSigns/DragonEmberAssembly', 'Bronze'),
 ('Shops/S01/ProjectingSigns/DragonEmberAssembly', 'Food_Charcoal'),
 ('Shops/S01/ProjectingSigns/DragonEmberAssembly', 'Food_Copper'),
 ('Shops/S01/ProjectingSigns/DragonEmberAssembly', 'Food_Oxblood'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Iron'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Bronze'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Food_Enamel'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Food_TileGreen'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Food_TileCream'),
 ('Shops/S02/ProjectingSigns/NoodleGuildAssembly', 'Noren3'),
 ('Shops/S03/ProjectingSigns/TravelerPotAssembly', 'Iron'),
 ('Shops/S03/ProjectingSigns/TravelerPotAssembly', 'Bronze'),
 ('Shops/S03/ProjectingSigns/TravelerPotAssembly', 'Food_Copper'),
 ('Shops/S03/ProjectingSigns/TravelerPotAssembly', 'Food_Chestnut'),
 ('Shops/S03/ProjectingSigns/TravelerPotAssembly', 'Food_TileCream'),
 ('Shops/S04/ProjectingSigns/WitchMoonAssembly', 'Iron'),
 ('Shops/S04/ProjectingSigns/WitchMoonAssembly', 'Bronze'),
 ('Shops/S04/ProjectingSigns/WitchMoonAssembly', 'Night_Walnut'),
 ('Shops/S04/ProjectingSigns/WitchMoonAssembly', 'Night_WineUpholstery'),
 ('Shops/S05/ProjectingSigns/MoonTeaTimberAssembly', 'Iron'),
 ('Shops/S05/ProjectingSigns/MoonTeaTimberAssembly', 'Bronze'),
 ('Shops/S05/ProjectingSigns/MoonTeaTimberAssembly', 'Food_Chestnut'),
 ('Shops/S05/ProjectingSigns/MoonTeaTimberAssembly', 'Food_PaleJoinery'),
 ('Shops/S06/ProjectingSigns/StarDistilleryAssembly', 'Iron'),
 ('Shops/S06/ProjectingSigns/StarDistilleryAssembly', 'Bronze'),
 ('Shops/S06/ProjectingSigns/StarDistilleryAssembly', 'Night_SmokyGlass'),
 ('Shops/S06/ProjectingSigns/StarDistilleryAssembly', 'Food_TileCream'),
 ('Shops/S07/ProjectingSigns/BardLyreAssembly', 'Iron'),
 ('Shops/S07/ProjectingSigns/BardLyreAssembly', 'Bronze'),
 ('Shops/S07/ProjectingSigns/BardLyreAssembly', 'Night_Walnut'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Iron'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Bronze'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Food_Chestnut'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Food_Enamel'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Food_TileCream'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Food_Oxblood'),
 ('Shops/S08/ProjectingSigns/FairyConfectionAssembly', 'Noren1'))
PART_ROLES={'Shops/S01/ProjectingSigns/DragonEmberAssembly': 'dimensional_emblem',
 'Shops/S02/ProjectingSigns/NoodleGuildAssembly': 'dimensional_emblem',
 'Shops/S03/ProjectingSigns/TravelerPotAssembly': 'dimensional_emblem',
 'Shops/S04/ProjectingSigns/WitchMoonAssembly': 'dimensional_emblem',
 'Shops/S05/ProjectingSigns/MoonTeaTimberAssembly': 'dimensional_emblem',
 'Shops/S06/ProjectingSigns/StarDistilleryAssembly': 'dimensional_emblem',
 'Shops/S07/ProjectingSigns/BardLyreAssembly': 'dimensional_emblem',
 'Shops/S08/ProjectingSigns/FairyConfectionAssembly': 'dimensional_emblem'}
MOTIFS=('dragon_ember','noodle_guild','traveler_pot','witch_hat','moon_tea_timber','star_distillery','bard_lyre','fairy_confection')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(value):return sha(encoded(value))
def key(row):return row['group'],row['material']
def _load(name,pin,root=None):
    path=(Path(root)/'Source' if root is not None else Path(__file__).resolve().parent)/'testdata'/name
    raw=path.read_bytes()
    if sha(raw)!=pin:raise ValueError('Immutable projecting-sign evidence changed: '+name)
    return json.loads(gzip.decompress(raw))
def before(root=None):
    import s05_pendant_contract as prior
    if prior.ORACLE_SHA256!=BEFORE_ORACLE_SHA256:raise ValueError('Immutable v2.18 after oracle pin changed')
    pin=prior.load_oracle(root)
    if pin['nativeSha256']!=BEFORE_NATIVE_SHA256 or pin['glbSha256']!=BEFORE_GLB_SHA256:raise ValueError('Wrong accepted v2.18 predecessor')
    value=_load(BEFORE_NAME,BEFORE_SHA256,root)
    if value['nativeSha256']!=BEFORE_NATIVE_SHA256 or value['glbSha256']!=BEFORE_GLB_SHA256:raise ValueError('Invalid projecting-sign before identity')
    if digest(value['manifest'])!=pin['manifestSha256'] or digest(value['rows'])!=pin['arrayRowsSha256']:raise ValueError('Before evidence is not the exact accepted v2.18 arrays/metadata')
    return value

def requested(m):
    f=m.get('features',{})
    return (isinstance(f,dict) and FEATURE in f) or METADATA in m or m.get('version')==VERSION

def validate_gate(m):
    f=m.get('features',{})
    if not isinstance(f,dict) or f.get(FEATURE) is not True:
        return [dict(reason='Projecting signs support literal true only; use the immutable v2.18 snapshot for rollback')]
    if m.get('version')!=VERSION or any(f.get(n) is not True for n in ('shop_personality','shop_rpg_identity','venue_lighting_identity','s05_pendant_refinement')):
        return [dict(reason='Projecting signs require version 2.19.0 and exact prior v2.18 true state')]
    info=m.get(METADATA)
    if not isinstance(info,dict) or set(info)!={'schema','version','baselineVersion','baselineNativeSha256','sourceSha256','venues'}:
        return [dict(reason='Exact projecting-sign provenance fields required')]
    if type(info['schema']) is not int or info['schema']!=1 or info['version']!=VERSION or info['baselineVersion']!='2.18.0' or info['baselineNativeSha256']!=BEFORE_NATIVE_SHA256:
        return [dict(reason='Wrong projecting-sign provenance schema/version/baseline')]
    if not isinstance(info['sourceSha256'],str) or len(info['sourceSha256'])!=64 or any(x not in '0123456789abcdef' for x in info['sourceSha256']):
        return [dict(reason='Invalid exact projecting-sign source checksum')]
    return []

def load_oracle(root=None):
    if ORACLE_SHA256.startswith('UNFROZEN'):raise ValueError('Projecting-sign art is not independently accepted and frozen')
    pin=_load(ORACLE_NAME,ORACLE_SHA256,root)
    if pin.get('schema')!=1 or pin.get('version')!=VERSION or pin.get('beforeNativeSha256')!=BEFORE_NATIVE_SHA256 or pin.get('beforeOracleSha256')!=BEFORE_ORACLE_SHA256:
        raise ValueError('Invalid projecting-sign after oracle schema')
    if tuple(map(tuple,pin['addedKeys']))!=KEYS or tuple(key(r) for r in pin['addedRows'])!=KEYS:raise ValueError('After oracle differs from explicit projecting-sign roster')
    if len(pin['manifestFieldOrder'])!=len(pin['manifestFieldHashes']) or set(pin['manifestFieldOrder'])!=set(pin['manifestFieldHashes']):raise ValueError('After oracle must authenticate every metadata field exactly once')
    if digest(pin['rows'])!=pin['rowsSha256']:raise ValueError('After oracle row fingerprint is inconsistent')
    return pin

def _failure(reason,**kw):return False,dict(passed=False,errors=[dict(reason=reason,**kw)])
def _counter_error(rows,m):
    if (type(m.get('visualMeshCount')) is not int or type(m.get('visualTriangles')) is not int
        or m['visualMeshCount']!=len(rows) or any(type(r.get('triangles')) is not int or r['triangles']<0 for r in rows)
        or m['visualTriangles']!=sum(r['triangles'] for r in rows)):
        return 'Actual projecting-sign native counters mismatch'

def _metadata_error(m,pin):
    hashes=pin['manifestFieldHashes']
    if set(m)!=set(hashes):return 'Exact current top-level metadata field roster changed'
    # Small/high-impact fields precede crown/floor test data. Invalid rows and
    # common metadata mutations never rehash the multi-megabyte full manifest.
    for field in pin['manifestFieldOrder']:
        if digest(m[field])!=hashes[field]:return 'Exact approved current metadata changed: '+field

def validate_summaries(rows,m,*,oracle=None):
    try:
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        reason=_counter_error(rows,m)
        if reason:return _failure(reason)
        pin=load_oracle() if oracle is None else oracle
        actual=[{f:r.get(f) for f in FIELDS} for r in rows]
        if digest(actual)!=pin['rowsSha256']:return _failure('Exact approved current native rows/order changed')
        reason=_metadata_error(m,pin)
        if reason:return _failure(reason)
        return True,dict(passed=True,errors=[],oracleSha256=ORACLE_SHA256,beforeNativeSha256=BEFORE_NATIVE_SHA256,addedBatches=len(KEYS))
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))

def validate_metadata(m,*,oracle=None):
    try:
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        reason=_metadata_error(m,load_oracle() if oracle is None else oracle)
        return _failure(reason) if reason else (True,dict(passed=True,errors=[]))
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))

def normalize_summaries(rows,m):
    if not requested(m):return rows,m,[],None
    ok,report=validate_summaries(rows,m)
    if not ok:return rows,m,report['errors'],report
    old=before()
    return [{f:r[f] for f in FIELDS} for r in old['rows']],copy.deepcopy(old['manifest']),[],report

def audit_scope(rows,m,*,prior=None):
    """Narrow proposal scope only. Never authorizes or freezes unreviewed art."""
    try:
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        reason=_counter_error(rows,m)
        if reason:return _failure(reason)
        old=before() if prior is None else prior;om=old['manifest']
        def check(value,reason,**kw):
            if not value:errors.append(dict(reason=reason,**kw))
        lookup={key(r):r for r in rows};oldmap={key(r):r for r in old['rows']};new=set(KEYS)
        check(bool(new) and len(KEYS)==len(new),'Explicit added key roster is not ready/unique')
        check(len(rows)==len(lookup)==len(oldmap)+len(new) and set(lookup)==set(oldmap)|new,'Exact additive native key roster changed')
        check(not(new&set(oldmap)),'Added key overlaps immutable baseline')
        check([key(r) for r in rows if key(r) not in new]==[key(r) for r in old['rows']],'Existing native record order changed')
        for k,r in oldmap.items():
            check(lookup.get(k)==r,'Existing native geometry/UV/Color32/indices changed',key=k)
        if errors:return False,dict(passed=False,errors=errors)
        added=[lookup[k] for k in KEYS];info=m[METADATA];venues=info['venues']
        check(isinstance(venues,list) and [v.get('shop') for v in venues]==[f'S{i:02d}' for i in range(1,9)],'Exactly eight ordered venue sign records required')
        if errors:return False,dict(passed=False,errors=errors)
        reported=[tuple(k) for v in venues for k in v['keys']]
        check(reported==list(KEYS),'Venue metadata key inventory differs from explicit added roster')
        check(all(v['motif']==MOTIFS[i] for i,v in enumerate(venues)),'Venue dimensional motif inventory changed')
        source_vertices=0
        for v in venues:
            actual=[lookup[tuple(k)] for k in v['keys']]
            check(type(v.get('sourceVertexCount')) is int and v['sourceVertexCount']>0,'Invalid exact source vertex counter',shop=v['shop'])
            source_vertices+=v['sourceVertexCount']
            check(type(v.get('triangleCount')) is int and v['triangleCount']==sum(r['triangles'] for r in actual),'Venue triangle count differs from actual added records',shop=v['shop'])
            check(type(v.get('batchCount')) is int and v['batchCount']==len(actual),'Venue batch count differs from actual records',shop=v['shop'])
        delta_tri=sum(r['triangles'] for r in added);delta_v=sum(r['vertices'] for r in added)
        restored=dict(m);restored.pop(METADATA);restored['version']=om['version']
        restored['features']=dict(m['features']);restored['features'].pop(FEATURE)
        restored['visualMeshCount']=om['visualMeshCount'];restored['visualTriangles']=om['visualTriangles']
        av=m['altitudeProfile']['visuals'];ov=om['altitudeProfile']['visuals']
        check(all(type(av.get(f)) is int for f in ('transformedBatches','transformedVertices')),'Altitude added counters must remain literal integers')
        check(av['transformedBatches']==ov['transformedBatches']+len(KEYS),'Altitude batch delta must equal exact added source keys')
        check(av['transformedVertices']==ov['transformedVertices']+source_vertices,'Altitude vertex delta must equal exact added source vertices')
        restored['altitudeProfile']=dict(m['altitudeProfile']);restored['altitudeProfile']['visuals']=dict(av)
        for f in ('transformedBatches','transformedVertices'):restored['altitudeProfile']['visuals'][f]=ov[f]
        repair=m['normalUvRepairs']-om['normalUvRepairs']
        check(type(m['normalUvRepairs']) is int and type(repair) is int and repair>=0,'Invalid added normal-UV repair counter')
        restored['normalUvRepairs']=om['normalUvRepairs']
        au=m['meshOptimization']['unused'];ou=om['meshOptimization']['unused']
        check(all(type(au.get(f)) is int for f in ('modifiedBatches','removedVertices','savedNativeBytes')),'Added compaction aggregate counters must remain literal integers')
        records=[r for r in au['batches'] if key(r) in new]
        check([r for r in au['batches'] if key(r) not in new]==ou['batches'],'Existing vertex-compaction records changed')
        check(len({key(r) for r in records})==len(records),'Duplicate added compaction record')
        removed=0
        for r in records:
            check(set(r)=={'group','material','beforeVertices','afterVertices','triangles','savedNativeBytes'},'Unexpected added compaction record fields')
            check(all(type(r[f]) is int for f in ('beforeVertices','afterVertices','triangles','savedNativeBytes')),'Invalid compaction counter types')
            count=r['beforeVertices']-r['afterVertices'];removed+=count
            check(count>0 and r['afterVertices']==lookup[key(r)]['vertices'] and r['triangles']==lookup[key(r)]['triangles'] and r['savedNativeBytes']==24*count,'Added compaction counters differ from actual native')
        check(au['modifiedBatches']==ou['modifiedBatches']+len(records) and au['removedVertices']==ou['removedVertices']+removed and au['savedNativeBytes']==ou['savedNativeBytes']+24*removed,'Exact added compaction aggregate counters changed')
        check(delta_v==source_vertices+3*repair-removed,'Final added vertex count must equal source plus exact UV splits minus removed vertices')
        restored['meshOptimization']=dict(m['meshOptimization']);restored['meshOptimization']['unused']=dict(au)
        for f in ('batches','modifiedBatches','removedVertices','savedNativeBytes'):restored['meshOptimization']['unused'][f]=ou[f]
        check(set(restored)==set(om),'Top-level metadata outside exact additive sign scope changed')
        large={'crownStairs','wallTests','floorTests','guards'}
        for field in sorted(om,key=lambda k:(k in large,k)):
            if field not in restored or digest(restored[field])!=old['manifestFieldHashes'][field]:
                check(False,'Metadata outside exact additive sign counters changed',field=field)
                break
        return not errors,dict(passed=not errors,errors=errors,addedKeys=[list(k) for k in KEYS],preservedNativeBatches=len(oldmap),addedTriangles=delta_tri,addedSourceVertices=source_vertices,addedNativeVertices=delta_v,addedNormalUvRepairs=repair,addedCompactionRemovedVertices=removed)
    except (ValueError,KeyError,TypeError,OSError,IndexError) as e:return _failure(str(e))

def validate_native(root,m,batches=None,*,check_dependencies=True):
    try:
        from peer_culling_contract import read_visual
        import rpg_identity_contract as rpg
        import s05_pendant_contract as prior_contract
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        root=Path(root);pin=load_oracle(root)
        if batches is None:batches=read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
        rows=rpg.summarize_batches(batches);ok,report=validate_summaries(rows,m,oracle=pin)
        if not ok:return ok,report
        errors=report['errors'];old=before(root)
        if digest(rows)!=pin['arrayRowsSha256']:errors.append(dict(reason='Exact current per-array native payload hashes changed'))
        if sha((root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes())!=pin['nativeSha256']:errors.append(dict(reason='Exact approved serialized native bytes changed'))
        if sha((root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes())!=old['collisionSha256']:errors.append(dict(reason='Immutable collision bytes changed'))
        _,scope=audit_scope(rows,m,prior=old);report['scope']=scope;errors.extend(scope['errors'])
        if check_dependencies:
            for rel,wanted in pin['dependencies'].items():
                p=root/rel
                if not p.is_file() or sha(p.read_bytes())!=wanted:errors.append(dict(reason='Exact sign source/runtime/texture dependency changed',path=rel))
            for prefix in ('Assets/TreeTopYokocho/Textures/','Source/fonts/'):
                actual={str(p.relative_to(root)) for p in (root/prefix).rglob('*') if p.is_file() and p.suffix!='.meta'}
                if actual!={p for p in pin['dependencies'] if p.startswith(prefix)}:errors.append(dict(reason='Exact texture/font roster changed',path=prefix))
            from rpg_runtime_compatibility import verify_runtime
            verify_runtime(root)
        if not errors:
            ok,prior=prior_contract.validate_summaries([{f:r[f] for f in FIELDS} for r in old['rows']],old['manifest'])
            report['priorS05Admission']=prior
            if not ok:errors.extend(prior['errors'])
        report['passed']=not errors
        return not errors,report
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))
