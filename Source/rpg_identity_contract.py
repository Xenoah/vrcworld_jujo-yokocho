"""Outer exact v2.17 admission, before immutable v2.16 and earlier gates.

No prefix exemption, regenerated historical baseline or production inverse.
The after checkpoint is deliberately fail-closed until independently approved.
"""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

VERSION='2.17.0'
FLAGS=('shop_rpg_identity','venue_lighting_identity')
BEFORE_NAME='rpg_identity_before_2_16.json.gz'
BEFORE_SHA256='a19dc9018be31e778652134706f177edf1d43510828f4ff0ed3051b9a2c2bd6f'
BEFORE_NATIVE_SHA256='f52f44353420638bb500afd37f04b9c55d7f30ab4da4c369ad4b4c98080e3c46'
ORACLE_NAME='rpg_identity_after_2_17.json.gz'
ORACLE_SHA256='04463740b720392ebc4cf65d941a9e1e30356fd21f711dbae2b1f407f602caf3'
ATLASES=('Assets/TreeTopYokocho/Textures/food_venue_signs.png','Assets/TreeTopYokocho/Textures/nightlife_signs.png')
BINDINGS=(
 ('Shops/S01/Personality/JoineryFinish','Food_Paper','VenueLight_S01_TaskDiffuser'),
 ('Shops/S01/Personality/CharcoalSigns','RedLantern','VenueLight_S01_EntryPaper'),
 ('Shops/S02/Personality/JoineryFinish','Food_Paper','VenueLight_S02_TaskDiffuser'),
 ('Shops/S03/Personality/JoineryFinish','Food_Paper','VenueLight_S03_PotDiffuser'),
 ('Shops/S03/Personality/OdenSigns','RedLantern','VenueLight_S03_EntryPaper'),
 ('Shops/S04/Personality/MedallionCeiling','WarmWindow','VenueLight_S04_PearlDiffuser'),
 ('Shops/S04/Personality/MedallionCeiling','Ceramic','VenueLight_S04_PlumShade'),
 ('Shops/S05/Personality/TeaSigns','Food_Paper','VenueLight_S05_MoonDiffuser'),
 ('Shops/S05/Personality/TeaPavilion','Food_Paper','VenueLight_S05_MoonClerestory'),
 ('Shops/S06/Personality/PendantCeiling','WarmWindow','VenueLight_S06_CyanDiffuser'),
 ('Shops/S07/Personality/AcousticSlatCeiling','WarmWindow','VenueLight_S07_IndigoDiffuser'),
 ('Shops/S08/Personality/JoineryFinish','Food_Paper','VenueLight_S08_IvoryDiffuser'),
)
# Only authoring modules explicitly changed by this revision; each gets an exact
# after hash. All previously frozen shaders, loaders, textures and oracles remain.
SOURCE_CHANGES=('Source/build_world.py','Source/shop_personality.py','Source/food_venues.py',
 'Source/nightlife_venues.py','Source/render_preview.py','Source/fantasy_preview.py',
 'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs')
NEW_SOURCES=('Source/rpg_shop_identities.py','Source/venue_lighting.py',
 'Assets/TreeTopYokocho/Editor/VenueLightingProfile.cs','Assets/TreeTopYokocho/Data/VenueLighting.json')
SIGN_KEYS=(('Shops/S01/Personality/CharcoalSigns','Food_Sign'),('Shops/S02/Personality/NoodleSigns','Food_Sign'),('Shops/S03/Personality/OdenSigns','Food_Sign'),('Shops/S04/Personality/Signage','Night_Print'),('Shops/S05/Personality/TeaSigns','Food_Sign'),('Shops/S06/Personality/Signage','Night_Print'),('Shops/S07/Personality/Signage','Night_Print'),('Shops/S08/Personality/ConfectionerSigns','Food_Sign'))
FIELDS=('group','material','vertices','triangles','geometrySha256','attributesAndIndicesSha256')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def key(row):return row['group'],row['material']
def digest(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def _load(name,expected,root=None):
    path=(Path(root)/'Source' if root is not None else Path(__file__).resolve().parent)/'testdata'/name
    raw=path.read_bytes()
    if sha(raw)!=expected:raise ValueError('Immutable RPG checkpoint changed: '+name)
    return json.loads(gzip.decompress(raw))
def load_before(root=None):
    before=_load(BEFORE_NAME,BEFORE_SHA256,root)
    if before['nativeSha256']!=BEFORE_NATIVE_SHA256 or len(before['rows'])!=1106 or len(before['signKeys'])!=13:
        raise ValueError('Invalid immutable v2.16 evidence')
    return before

def requested(manifest):
    import projecting_sign_contract as signs
    import s05_pendant_contract as pendant
    if signs.requested(manifest) or pendant.requested(manifest):return True
    features=manifest.get('features',{})
    return (isinstance(features,dict) and any(f in features for f in FLAGS)) or any(k in manifest for k in ('shopRpgIdentity','venueLighting')) or manifest.get('version')==VERSION

def validate_gate(manifest):
    import projecting_sign_contract as signs
    if signs.requested(manifest):return signs.validate_gate(manifest)
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):return pendant.validate_gate(manifest)
    if not requested(manifest):return []
    f=manifest.get('features',{})
    if not isinstance(f,dict) or any(type(f.get(k)) is not bool for k in FLAGS):
        return [dict(reason='Both RPG feature flags must be present literal Booleans')]
    if manifest.get('version')!=VERSION:return [dict(reason='Every newly built RPG variant must use version 2.17.0')]
    if f.get('shop_personality') is not True:return [dict(reason='RPG revision requires reviewed shop personality')]
    for flag,metadata in zip(FLAGS,('shopRpgIdentity','venueLighting')):
        if (metadata in manifest)!=f[flag]:return [dict(reason='Feature and metadata presence disagree',field=metadata)]
    return []
def variant_key(manifest):return ''.join('1' if manifest['features'][k] else '0' for k in FLAGS)
def load_oracle(root=None):
    if ORACLE_SHA256.startswith('UNFROZEN'):raise ValueError('RPG art checkpoint is not independently accepted and frozen')
    oracle=_load(ORACLE_NAME,ORACLE_SHA256,root)
    if set(oracle)!= {'schema','version','beforeNativeSha256','variants'} or oracle['schema']!=1 or oracle['version']!=VERSION or oracle['beforeNativeSha256']!=BEFORE_NATIVE_SHA256 or set(oracle['variants'])!={'00','01','10','11'}:
        raise ValueError('Invalid four-variant RPG checkpoint schema')
    return oracle

def summarize_batches(batches):
    from peer_culling_contract import summarize
    rows=[]
    for batch in batches:
        row=summarize(batch)
        row['arraySha256']={a:sha(np.asarray(batch[a],dtype=t).tobytes()) for a,t in [('vertices','<f4'),('uv','<f4'),('colors','u1'),('faces','<u4')]}
        rows.append(row)
    return rows

def audit_scope(rows,manifest,*,before=None):
    import projecting_sign_contract as signs
    if signs.requested(manifest):return signs.audit_scope(rows,manifest)
    """Independent scope check, never an art approval or after oracle creator."""
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):return pendant.audit_scope(rows,manifest)
    before=load_before() if before is None else before
    errors=validate_gate(manifest)
    if errors:return False,dict(errors=errors)
    f=manifest['features'];identity,lighting=(f[x] for x in FLAGS)
    def check(good,reason,**details):
        if not good:errors.append(dict(reason=reason,**details))
    old=before['manifest'];restored=copy.deepcopy(manifest)
    restored['version']=old['version']
    from rpg_runtime_compatibility import load_oracle as runtime_oracle, BUILDER
    check(restored['meshOptimization']['cityCaps']['builderSha256']==runtime_oracle()['dependencies'][BUILDER],'City-cap builder provenance differs from source-reviewed runtime')
    restored['meshOptimization']['cityCaps']['builderSha256']=old['meshOptimization']['cityCaps']['builderSha256']
    for flag in FLAGS:restored['features'].pop(flag,None)
    restored.pop('shopRpgIdentity',None);restored.pop('venueLighting',None)
    remap={(g,src):(g,dst) for g,src,dst in BINDINGS} if lighting else {}
    signkeys=set(SIGN_KEYS)
    check(len(rows)==len(before['rows']),'Native record count changed')
    for index,(a,b) in enumerate(zip(before['rows'],rows)):
        check(key(b)==remap.get(key(a),key(a)),'Native key/order outside exact fixture remap changed',index=index)
        allowed={'uv'} if identity and key(a) in signkeys else set()
        for attr in ('vertices','faces','colors','uv'):
            if attr not in allowed:check(b.get('arraySha256',{}).get(attr)==a['arraySha256'][attr],'Native array outside owned sign UV changed',index=index,array=attr)
        check(a['vertices']==b['vertices'] and a['triangles']==b['triangles'] and a['geometrySha256']==b['geometrySha256'],'Geometry/count changed',index=index)
    check(manifest.get('visualMeshCount')==len(rows) and manifest.get('visualTriangles')==sum(r['triangles'] for r in rows),'Actual native counters mismatch')
    if identity:
        info=manifest.get('shopRpgIdentity',{})
        check(set(info)=={'schema','version','baselineVersion','names','sourceSha256','atlasSha256','fontManifestSha256'},'Identity provenance schema changed')
        check(info.get('schema')==1 and type(info.get('schema')) is int and info.get('version')==VERSION and info.get('baselineVersion')=='2.16.0','Identity provenance version changed')
    shops=restored.get('shopPersonality',{}).get('shops',[])
    oldshops=old['shopPersonality']['shops']
    if identity:
        check(manifest['shopRpgIdentity'].get('names')==[{'id':s['id'],'displayName':s['displayName']} for s in shops],'All eight RPG display names must agree with identity provenance')
    check(len(shops)==8,'Exactly eight existing shop descriptors required')
    for a,b in zip(oldshops,shops):
        # Source provenance changes in every newly built variant, names only when enabled.
        if identity:b['displayName']=a['displayName']
        b['sourceSha256']=a['sourceSha256']
        if lighting:
            indices=a['world']['lightIndices']
            for space in ('local','world'):
                for index,light in zip(indices,b[space]['lights']):
                    check(light.get('venueLighting')==manifest['lights'][index].get('venueLighting') and 'venueLighting' in light,'Local/world/global fixture identity mismatch',shop=a['id'],space=space,index=index)
                    light.pop('venueLighting',None)
    if lighting:
        for i,light in enumerate(restored['lights']):
            if 88<=i<103:light.pop('venueLighting',None)
        names={dst for _,_,dst in BINDINGS}
        originals={m['name']:m for m in old['materials']}
        clones=[m for m in restored['materials'] if m['name'] in names]
        check(len(clones)==12 and {m['name'] for m in clones}==names,'Exact twelve fixture material clones required')
        source={dst:src for _,src,dst in BINDINGS}
        for clone in clones:
            a=originals[source[clone['name']]]
            check({k:v for k,v in clone.items() if k not in ('name','color','emission','shader')}=={k:v for k,v in a.items() if k not in ('name','color','emission','shader')},'Fixture clone changed unrelated material fields',material=clone['name'])
        restored['materials']=[m for m in restored['materials'] if m['name'] not in names]
    check(digest(restored)==digest(old),'Manifest field outside exact identity/light/provenance scope changed')
    return not errors,dict(passed=not errors,errors=errors,actualNativeBatches=len(rows),ownedSignBatches=8 if identity else 0,ownedFixtureRemaps=12 if lighting else 0,ownedExistingLights=15 if lighting else 0)

def validate_summaries(rows,manifest,*,oracle=None,before=None):
    import projecting_sign_contract as signs
    if signs.requested(manifest):return signs.validate_summaries(rows,manifest)
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):return pendant.validate_summaries(rows,manifest)
    try:
        errors=validate_gate(manifest)
        if errors:return False,dict(errors=errors)
        # Invalid actual counts cannot become valid through any after oracle.
        # Fail before loading its large four-variant metadata, preserving every
        # historical missing/duplicate case without repeated decompression.
        if (type(manifest.get('visualMeshCount')) is not int or type(manifest.get('visualTriangles')) is not int
                or manifest['visualMeshCount']!=len(rows) or manifest['visualTriangles']!=sum(r['triangles'] for r in rows)):
            return False,dict(passed=False,errors=[dict(reason='Actual current native counts do not match manifest')])
        oracle=load_oracle() if oracle is None else oracle
        expected=oracle['variants'][variant_key(manifest)]
        actual=[{k:r.get(k) for k in FIELDS} for r in rows]
        wanted=[{k:r[k] for k in FIELDS} for r in expected['rows']]
        if digest(actual)!=digest(wanted):
            # Once current rows differ, no manifest can authorize projection.
            # Positive rows still require exact full metadata authentication.
            return False,dict(passed=False,errors=[dict(reason='Exact approved current RPG native rows/order changed')])
        if digest(manifest)!=digest(expected['manifest']):errors.append(dict(reason='Exact approved current RPG manifest changed'))
        return not errors,dict(passed=not errors,errors=errors,variant=variant_key(manifest),oracleSha256=ORACLE_SHA256)
    except (ValueError,KeyError,TypeError,OSError) as exc:return False,dict(passed=False,errors=[dict(reason=str(exc))])

def normalize_summaries(rows,manifest):
    import projecting_sign_contract as signs
    rows,manifest,sign_errors,sign_detail=signs.normalize_summaries(rows,manifest)
    if sign_errors:return rows,manifest,sign_errors,sign_detail
    import s05_pendant_contract as pendant
    rows,manifest,pendant_errors,pendant_detail=pendant.normalize_summaries(rows,manifest)
    if pendant_errors:return rows,manifest,pendant_errors,pendant_detail
    if not requested(manifest):return rows,manifest,[],None
    ok,detail=validate_summaries(rows,manifest)
    if not ok:return rows,manifest,detail['errors'],detail
    before=load_before()
    # This historical-only view never describes current rendering/physics.
    projected=[{k:r[k] for k in FIELDS} for r in before['rows']]
    return projected,copy.deepcopy(before['manifest']),[],detail

def validate_metadata(manifest,*,oracle=None):
    import projecting_sign_contract as signs
    if signs.requested(manifest):return signs.validate_metadata(manifest)
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):return pendant.validate_metadata(manifest)
    try:
        errors=validate_gate(manifest)
        if not errors:
            oracle=load_oracle() if oracle is None else oracle
            if digest(manifest)!=digest(oracle['variants'][variant_key(manifest)]['manifest']):errors.append(dict(reason='Exact approved current RPG metadata changed'))
        return not errors,dict(passed=not errors,errors=errors)
    except (ValueError,KeyError,TypeError,OSError) as exc:return False,dict(passed=False,errors=[dict(reason=str(exc))])

def validate_native(root,manifest,batches=None,*,check_dependencies=True):
    import projecting_sign_contract as signs
    if signs.requested(manifest):return signs.validate_native(root,manifest,batches,check_dependencies=check_dependencies)
    import s05_pendant_contract as pendant
    if pendant.requested(manifest):return pendant.validate_native(root,manifest,batches,check_dependencies=check_dependencies)
    try:
        from peer_culling_contract import read_visual
        root=Path(root);before=load_before(root);oracle=load_oracle(root)
        if batches is None:batches=read_visual(root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
        rows=summarize_batches(batches);ok,detail=validate_summaries(rows,manifest,oracle=oracle,before=before)
        if not ok:return ok,detail
        variant=oracle['variants'][variant_key(manifest)]
        scope_ok,scope=audit_scope(rows,manifest,before=before);detail['scope']=scope
        errors=detail['errors'];errors.extend(scope['errors'])
        if sha((root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes').read_bytes())!=variant['nativeSha256']:errors.append(dict(reason='Serialized native artifact differs from exact approved bytes'))
        if digest(rows)!=digest(variant['rows']):errors.append(dict(reason='Exact current per-array RPG payload hashes changed'))
        if sha((root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes())!=before['collisionSha256']:errors.append(dict(reason='Immutable collision bytes changed'))
        if check_dependencies:
            for rel,expected in variant['dependencies'].items():
                path=root/rel
                if not path.is_file() or sha(path.read_bytes())!=expected:errors.append(dict(reason='Exact RPG source/texture/runtime dependency changed',path=rel))
            for prefix in ('Assets/TreeTopYokocho/Textures/','Source/fonts/'):
                actual={str(p.relative_to(root)) for p in (root/prefix).rglob('*') if p.is_file() and p.suffix!='.meta'}
                wanted={p for p in variant['dependencies'] if p.startswith(prefix)}
                if actual!=wanted:errors.append(dict(reason='Exact RPG texture/font roster changed',path=prefix))
            from rpg_runtime_compatibility import verify_runtime
            verify_runtime(root)
        # Older contracts receive authenticated immutable v2.16 data, not a
        # wildcard exemption. Their own pinned before/after checkpoints still run.
        if not errors:
            import shop_personality_contract as prior
            prior_rows=[{k:r[k] for k in FIELDS} for r in before['rows']]
            oldok,oldreport=prior.validate_summaries(prior_rows,before['manifest'])
            metaok,metareport=prior.validate_metadata(before['manifest'])
            detail['priorShopAdmission']=oldreport;detail['priorShopMetadata']=metareport
            if not oldok:errors.extend(oldreport['errors'])
            if not metaok:errors.extend(metareport['errors'])
        detail['passed']=not errors
        return not errors,detail
    except (ValueError,KeyError,TypeError,OSError) as exc:return False,dict(passed=False,errors=[dict(reason=str(exc))])
