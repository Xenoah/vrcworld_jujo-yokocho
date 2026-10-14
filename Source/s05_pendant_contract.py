"""True-only exact v2.18 S05 pendant delta above immutable v2.17 state11.

No old oracle is replaced. Current records/metadata/source authenticate before
historical projection. This module never reconstructs geometry for admission.
"""
import copy,gzip,hashlib,json
from pathlib import Path
FEATURE='s05_pendant_refinement'
VERSION='2.18.0'
BEFORE_NATIVE_SHA256='104fe5962b2a19287a9c255846ef425637c077d3d5647096f1c2a3128e8a6358'
BEFORE_GLB_SHA256='5fe12d9a4ba36163aab0d1e360894064b40498221c94aa04dbe25a90dd936d8d'
BEFORE_ORACLE_SHA256='04463740b720392ebc4cf65d941a9e1e30356fd21f711dbae2b1f407f602caf3'
ORACLE_NAME='s05_pendant_after_2_18.json.gz'
ORACLE_SHA256='50bf06fbc5f6d85b00e841c7d166cad167682367d1a3908e612d959913993a0d'
OLD_KEY=('Shops/S05/Personality/TeaSigns','Food_PaleJoinery')
NEW_KEY=('Shops/S05/Personality/TeaSigns','DarkTimber')
SOURCE_CHANGES=('Source/build_world.py','Source/shop_personality.py','Source/food_venues.py')
FIELDS=('group','material','vertices','triangles','geometrySha256','attributesAndIndicesSha256')
FOOD_IDS=('S01','S02','S03','S05','S08')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def key(row):return row['group'],row['material']
def requested(m):
    f=m.get('features',{})
    return (isinstance(f,dict) and FEATURE in f) or 's05PendantRefinement' in m or m.get('version')==VERSION

def validate_gate(m):
    f=m.get('features',{})
    if not isinstance(f,dict) or f.get(FEATURE) is not True:
        return [dict(reason='S05 refinement supports literal true only; use the immutable v2.17 snapshot for rollback')]
    if m.get('version')!=VERSION or any(f.get(k) is not True for k in ('shop_personality','shop_rpg_identity','venue_lighting_identity')):
        return [dict(reason='S05 refinement requires version 2.18.0 and exact prior RPG state11')]
    if 's05PendantRefinement' not in m:return [dict(reason='Missing S05 refinement provenance')]
    return []

def before(root=None):
    import rpg_identity_contract as rpg
    if rpg.ORACLE_SHA256!=BEFORE_ORACLE_SHA256:raise ValueError('Immutable prior RPG oracle pin changed')
    value=rpg.load_oracle(root)['variants']['11']
    if value['nativeSha256']!=BEFORE_NATIVE_SHA256 or value['glbSha256']!=BEFORE_GLB_SHA256:raise ValueError('Invalid immutable prior state11')
    return value

def load_oracle(root=None):
    if ORACLE_SHA256.startswith('UNFROZEN'):raise ValueError('S05 pendant art is not independently accepted and frozen')
    path=(Path(root)/'Source' if root is not None else Path(__file__).resolve().parent)/'testdata'/ORACLE_NAME
    raw=path.read_bytes()
    if sha(raw)!=ORACLE_SHA256:raise ValueError('Frozen S05 after oracle changed')
    pin=json.loads(gzip.decompress(raw))
    if pin.get('schema')!=1 or pin.get('version')!=VERSION or pin.get('beforeNativeSha256')!=BEFORE_NATIVE_SHA256:raise ValueError('Invalid S05 oracle schema')
    return pin

def _failure(reason):return False,dict(passed=False,errors=[dict(reason=reason)])
def validate_summaries(rows,m,*,oracle=None):
    try:
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        if (type(m.get('visualMeshCount')) is not int or type(m.get('visualTriangles')) is not int
            or m['visualMeshCount']!=len(rows) or m['visualTriangles']!=sum(r['triangles'] for r in rows)):
            return _failure('Actual S05 native counters mismatch')
        pin=load_oracle() if oracle is None else oracle
        summary=[{f:r.get(f) for f in FIELDS} for r in rows]
        if digest(summary)!=pin['rowsSha256']:return _failure('Exact approved current S05 native rows/order changed')
        if digest(m)!=pin['manifestSha256']:return _failure('Exact approved current S05 manifest changed')
        import rpg_identity_contract as rpg
        old=before();ok,prior_report=rpg.validate_summaries([{f:r[f] for f in FIELDS} for r in old['rows']],old['manifest'])
        return ok,dict(passed=ok,errors=prior_report['errors'],oracleSha256=ORACLE_SHA256,beforeNativeSha256=BEFORE_NATIVE_SHA256,priorRpgAdmission=prior_report)
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))

def validate_metadata(m,*,oracle=None):
    try:
        errors=validate_gate(m)
        if errors:return False,dict(passed=False,errors=errors)
        pin=load_oracle() if oracle is None else oracle
        if digest(m)!=pin['manifestSha256']:return _failure('Exact approved current S05 metadata changed')
        import rpg_identity_contract as rpg
        ok,report=rpg.validate_metadata(before()['manifest'])
        return ok,dict(passed=ok,errors=report['errors'],priorRpgMetadata=report)
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))

def normalize_summaries(rows,m):
    if not requested(m):return rows,m,[],None
    ok,report=validate_summaries(rows,m)
    if not ok:return rows,m,report['errors'],report
    old=before()
    return [{f:r[f] for f in FIELDS} for r in old['rows']],copy.deepcopy(old['manifest']),[],report

def audit_scope(rows,m,*,prior=None):
    """Proposal scope only; no after art approval or unpinned source exception."""
    errors=validate_gate(m)
    if errors:return False,dict(passed=False,errors=errors)
    old=before() if prior is None else prior;om=old['manifest']
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    oldrows={key(r):r for r in old['rows']};current={key(r):r for r in rows}
    check(len(rows)==len(current)==len(oldrows)+1,'Expected one exact added DarkTimber batch')
    check(set(current)==set(oldrows)|{NEW_KEY},'Unexpected missing/added batch identity')
    check([key(r) for r in rows if key(r)!=NEW_KEY]==[key(r) for r in old['rows']],'Existing native batch order changed')
    for k,r in oldrows.items():
        if k!=OLD_KEY:check(current.get(k)==r,'Unrelated native arrays changed',key=k)
    if OLD_KEY in current and NEW_KEY in current:
        check(current[OLD_KEY]['triangles']==oldrows[OLD_KEY]['triangles']-176,'Exactly four 44-triangle caps must leave pale joinery')
        check(current[NEW_KEY]['triangles']==176+144,'DarkTimber must contain four preserved caps and twelve 12-triangle stiles')
        check(current[OLD_KEY]['vertices']==146 and current[NEW_KEY]['vertices']==672,'Exact cap relocation/stile vertex counts changed')
    check(m.get('visualMeshCount')==len(rows) and m.get('visualTriangles')==sum(r['triangles'] for r in rows),'Actual S05 export counters mismatch')
    check(m.get('visualMeshCount')==om['visualMeshCount']+1 and m.get('visualTriangles')==om['visualTriangles']+144,'Expected +1 batch and +144 triangles')
    info=m['s05PendantRefinement'];food_sha=next(s['sourceSha256'] for s in m['shopPersonality']['shops'] if s['id']=='S05')
    expected_info=dict(schema=1,version=VERSION,baselineVersion='2.17.0',baselineNativeSha256=BEFORE_NATIVE_SHA256,sourceSha256=food_sha,capCount=4,stileCount=12,addedTriangles=144)
    check(digest(info)==digest(expected_info),'S05 provenance schema/value mismatch')
    restored=copy.deepcopy(m);restored['version']=om['version'];restored['features'].pop(FEATURE,None);restored.pop('s05PendantRefinement',None)
    restored['visualMeshCount']=om['visualMeshCount'];restored['visualTriangles']=om['visualTriangles']
    for actual,prior_shop in zip(restored['shopPersonality']['shops'],om['shopPersonality']['shops']):
        if actual['id'] in FOOD_IDS:actual['sourceSha256']=prior_shop['sourceSha256']
    # These are derived source counters, checked algebraically before restoring
    # their historical view. All other altitude/compaction policy stays exact.
    check(type(m.get('normalUvRepairs')) is int and m['normalUvRepairs']==om['normalUvRepairs'],'S05 refinement must not change UV repair count')
    vertex_delta=sum(r['vertices'] for r in rows)-sum(r['vertices'] for r in old['rows'])
    check(vertex_delta==288,'Exactly twelve 24-vertex stile boxes may be added')
    av=m['altitudeProfile']['visuals'];ov=om['altitudeProfile']['visuals']
    check(av['transformedBatches']==ov['transformedBatches']+1,'Altitude batch counter must reflect one added source batch')
    check(av['transformedVertices']==ov['transformedVertices']+288,'Altitude source vertex counter inconsistent with exported vertices and UV splits')
    restored['normalUvRepairs']=om['normalUvRepairs']
    restored['altitudeProfile']['visuals']['transformedBatches']=ov['transformedBatches'];restored['altitudeProfile']['visuals']['transformedVertices']=ov['transformedVertices']
    check(digest(restored)==digest(om),'Metadata outside exact S05 counters/source provenance changed')
    return not errors,dict(passed=not errors,errors=errors,changedKeys=[list(OLD_KEY)],addedKeys=[list(NEW_KEY)],triangleDelta=144)

def validate_native(root,m,batches=None,*,check_dependencies=True):
    try:
        from peer_culling_contract import read_visual
        import rpg_identity_contract as rpg
        root=Path(root);pin=load_oracle(root)
        if batches is None:batches=read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
        rows=rpg.summarize_batches(batches);ok,report=validate_summaries(rows,m,oracle=pin)
        if not ok:return ok,report
        errors=report['errors']
        if digest(rows)!=pin['arrayRowsSha256']:errors.append(dict(reason='Current S05 per-array payload hashes changed'))
        if sha((root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes())!=pin['nativeSha256']:errors.append(dict(reason='Current S05 serialized native bytes changed'))
        prior=before(root);scope_ok,scope=audit_scope(rows,m,prior=prior);report['scope']=scope;errors.extend(scope['errors'])
        if sha((root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes())!=pin['collisionSha256']:errors.append(dict(reason='Immutable collision bytes changed'))
        if check_dependencies:
            for rel,wanted in pin['dependencies'].items():
                p=root/rel
                if not p.is_file() or sha(p.read_bytes())!=wanted:errors.append(dict(reason='Exact S05 source/runtime/texture dependency changed',path=rel))
            from rpg_runtime_compatibility import verify_runtime
            verify_runtime(root)
            for prefix in ('Assets/TreeTopYokocho/Textures/','Source/fonts/'):
                actual={str(p.relative_to(root)) for p in (root/prefix).rglob('*') if p.is_file() and p.suffix!='.meta'}
                if actual!={p for p in pin['dependencies'] if p.startswith(prefix)}:errors.append(dict(reason='Exact texture/font roster changed',path=prefix))
        if not errors:
            ok,old_report=rpg.validate_summaries([{f:r[f] for f in FIELDS} for r in prior['rows']],prior['manifest'])
            mok,meta=rpg.validate_metadata(prior['manifest']);report['priorRpgAdmission']=old_report;report['priorRpgMetadata']=meta
            if not ok:errors.extend(old_report['errors'])
            if not mok:errors.extend(meta['errors'])
        report['passed']=not errors
        return not errors,report
    except (ValueError,KeyError,TypeError,OSError) as e:return _failure(str(e))
