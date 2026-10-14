"""Exact reviewed eight-shop replacement; no group-prefix exemption or inverse.

The production adapter authenticates actual revised native records and metadata
before projecting ONLY literal pinned shop summaries for legacy contracts.
An after oracle is not available until the integrator freezes visually accepted
source. Until then enabled admission fails closed; audit_proposal is diagnostic.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import numpy as np

FEATURE='shop_personality'
SCHEMA=1
VERSION='2.16.0'
BEFORE_NAME='shop_personality_before_2_15.json'
BEFORE_SHA256='ca4b07fbfe0bc6bad19a9f8ee218406bc3da85e7213978e140678da5f4d56870'
BEFORE_NATIVE_SHA256='d8124fa235ba3112b79a0ac04c3e7a5fd8d25a496cb798303d68ee08fd3d54c6'
RETAINED_NAME='shop_personality_retained_root_2_16.json'
RETAINED_SHA256='16afa5831a2815414bd10719be8f1e2b8e74c901d02fd2ecbf88560958d7958f'
ORACLE_NAME='shop_personality_after_2_16.json'
ORACLE_SHA256='6b039bba23205bf89c1d92bd391469b162f50c8775697e19389d142289a6ce9d'
SHOPS=('S01','S02','S03','S04','S05','S06','S07','S08')
SEAT_COUNTS=(6,6,5,6,8,6,6,6)
NIGHTLIFE=('S04','S06','S07')
FOOD=('S01','S02','S03','S05','S08')
FIELDS=('vertices','triangles','geometrySha256','attributesAndIndicesSha256')
MUTABLE_FIELDS=('version','features','materials','lights','steam','stations','solidBoxes',
                'shopCraft','meshOptimization','normalUvRepairs','visualMeshCount','visualTriangles','altitudeProfile')


def key(row):return row['group'],row['material']
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def requested(manifest):
    features=manifest.get('features',{})
    return isinstance(features,dict) and FEATURE in features

def enabled(manifest):
    features=manifest.get('features',{})
    return isinstance(features,dict) and features.get(FEATURE) is True

def validate_gate(manifest):
    features=manifest.get('features',{})
    if not isinstance(features,dict) or FEATURE not in features:
        return [] if 'shopPersonality' not in manifest else [dict(reason='Shop personality metadata requires its literal feature gate')]
    value=features[FEATURE]
    if value is False:
        return [] if 'shopPersonality' not in manifest else [dict(reason='Disabled shop personality cannot retain revised metadata')]
    if value is not True:return [dict(reason='features.shop_personality must be literal true or false')]
    return []

def _load(name,sha,root=None):
    path=(Path(root)/'Source' if root is not None else Path(__file__).resolve().parent)/'testdata'/name
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Frozen shop personality fixture changed: '+name)
    return json.loads(raw)

def load_before(root=None):
    before=_load(BEFORE_NAME,BEFORE_SHA256,root)
    rows=before['rows'];keys=[key(r) for r in rows];shop_keys=[tuple(k) for k in before['shopKeys']]
    if (before['nativeSha256']!=BEFORE_NATIVE_SHA256 or len(rows)!=1058 or len(keys)!=len(set(keys))
        or len(shop_keys)!=243 or len(set(shop_keys))!=243 or not set(shop_keys)<=set(keys)
        or before['shopLightIndices']!=list(range(88,128))):
        raise ValueError('Invalid immutable before schema')
    return before

def load_retained(root=None):
    data=_load(RETAINED_NAME,RETAINED_SHA256,root)
    rows=data['rows'];keys=[key(r) for r in rows]
    if len(rows)!=40 or len(set(keys))!=40 or data['beforeNativeSha256']!=BEFORE_NATIVE_SHA256:raise ValueError('Invalid exact retained-root fixture')
    return rows

def load_oracle(root=None):
    if ORACLE_SHA256.startswith('UNFROZEN'):raise ValueError('Shop personality after oracle is not visually accepted and frozen')
    data=_load(ORACLE_NAME,ORACLE_SHA256,root);before=load_before(root)
    keys=[key(r) for r in data['shopRows']]
    if (data.get('schema')!=SCHEMA or data.get('version')!=VERSION
        or data.get('beforeNativeSha256')!=BEFORE_NATIVE_SHA256 or len(keys)!=len(set(keys))
        or set(keys)&{key(r) for r in before['rows'] if key(r) not in set(map(tuple,before['shopKeys']))}):
        raise ValueError('Invalid exact approved shop replacement oracle')
    retained=load_retained(root);lookup={key(r):r for r in data['shopRows']}
    if any(lookup.get(key(r))!=r for r in retained):raise ValueError('Approved roster does not preserve exact outer-planter and underside brace payloads')
    return data

def _rows_errors(rows,expected):
    errors=[];counts=Counter(key(r) for r in rows);wanted={key(r):r for r in expected}
    missing=sorted(set(wanted)-set(counts));extra=sorted(set(counts)-set(wanted))
    duplicate=sorted(k for k,v in counts.items() if v!=1)
    if missing:errors.append(dict(reason='Missing exact native records',keys=missing))
    if extra:errors.append(dict(reason='Unexpected native records',keys=extra))
    if duplicate:errors.append(dict(reason='Duplicate native records',keys=duplicate))
    changed=[key(r) for r in rows if key(r) in wanted and any(r.get(f)!=wanted[key(r)].get(f) for f in FIELDS)]
    if changed:errors.append(dict(reason='Exact native attributes/index payload changed',keys=changed))
    return errors

def _actual_count_errors(rows,manifest):
    errors=[]
    for field,value in [('visualMeshCount',len(rows)),('visualTriangles',sum(r['triangles'] for r in rows))]:
        if type(manifest.get(field)) is not int or manifest[field]!=value:
            errors.append(dict(reason='Shop personality actual export count mismatch before projection',field=field,expected=value,actual=manifest.get(field)))
    return errors

def validate_summaries(rows,manifest,*,oracle=None,before=None):
    """Exact current-native admission. No normalization has occurred here."""
    import rpg_identity_contract as rpg
    if rpg.requested(manifest):
        ok,detail=rpg.validate_summaries(rows,manifest)
        if not ok:return ok,detail
        prior=rpg.load_before()
        ok,old_detail=validate_summaries([{k:r[k] for k in rpg.FIELDS} for r in prior['rows']],prior['manifest'],oracle=oracle,before=before)
        detail['priorShopAdmission']=old_detail
        if not ok:detail['errors'].extend(old_detail['errors'])
        detail['passed']=not detail['errors'];return detail['passed'],detail
    try:
        before=before or load_before();oracle=oracle or load_oracle();errors=_actual_count_errors(rows,manifest)
        if not enabled(manifest):errors.append(dict(reason='features.shop_personality must be literal true'))
        info=manifest.get('shopPersonality',{})
        if not isinstance(info,dict) or type(info.get('schema')) is not int or info.get('schema')!=SCHEMA or info.get('version')!=VERSION or info.get('baselineVersion')!='2.15.0':
            errors.append(dict(reason='Shop personality schema/version mismatch'))
        features=copy.deepcopy(before['manifest']['features']);features[FEATURE]=True
        if manifest.get('features')!=features:errors.append(dict(reason='Unapproved feature state in shop personality revision'))
        old=set(map(tuple,before['shopKeys']));nonshop=[r for r in before['rows'] if key(r) not in old]
        expected=nonshop+oracle['shopRows'];errors.extend(_rows_errors(rows,expected))
        if [list(key(r)) for r in rows]!=oracle['nativeKeyOrder']:errors.append(dict(reason='Exact approved native record order changed'))
        nonshop_lookup={key(r):r for r in nonshop}
        detail=dict(passed=not errors,errors=errors,oracleSha256=ORACLE_SHA256,beforeNativeSha256=BEFORE_NATIVE_SHA256,
                    actualNativeBatches=len(rows),actualNativeTriangles=sum(r['triangles'] for r in rows),
                    expectedNonshopBatches=len(nonshop),exactPreservedNonshopBatches=sum(nonshop_lookup.get(key(r))==r for r in rows),
                    legacyShopRecords=len(old),exactPreservedHerbBatches=32,exactPreservedUndersideBraceComponents=8,fullyRetiredLegacyShopKeys=203,approvedShopBatches=len(oracle['shopRows']),approvedNewPersonalityBatches=len(oracle['shopRows'])-40,
                    scope='Exact actual-native rows and counts before any legacy projection; all nonshop arrays exact; no Unity/VRChat claim')
        return not errors,detail
    except (ValueError,KeyError,TypeError,OSError) as exc:return False,dict(passed=False,errors=[dict(reason=str(exc))])

def normalize_summaries(rows,manifest):
    """Project only after authenticating exact approved current native payloads."""
    import rpg_identity_contract as rpg
    rows,manifest,rpg_errors,rpg_detail=rpg.normalize_summaries(rows,manifest)
    if rpg_errors:return rows,manifest,rpg_errors,rpg_detail
    gate_errors=validate_gate(manifest)
    if gate_errors:return rows,manifest,gate_errors,None
    if not enabled(manifest):return rows,manifest,[],None
    before=load_before();oracle=load_oracle();ok,detail=validate_summaries(rows,manifest,oracle=oracle,before=before)
    if not ok:return rows,manifest,detail['errors'],detail
    metadata_ok,metadata=validate_metadata(manifest,oracle=oracle,before=before)
    if not metadata_ok:
        detail['metadata']=metadata
        return rows,manifest,metadata['errors'],detail
    old=set(map(tuple,before['shopKeys']));lookup={key(r):r for r in rows}
    projected=[dict(r) if key(r) in old else lookup[key(r)] for r in before['rows']]
    m=dict(manifest);m['visualMeshCount']=len(projected);m['visualTriangles']=sum(r['triangles'] for r in projected)
    # Legacy optimizations expect their own old per-shop optimization metadata.
    # Preserve current manifest outside this explicit historical-only view.
    m['meshOptimization']=copy.deepcopy(manifest['meshOptimization'])
    m['meshOptimization']['unused']=copy.deepcopy(before['manifest']['meshOptimization']['unused'])
    detail['legacyProjectionBatches']=len(projected);detail['legacyProjectionTriangles']=m['visualTriangles']
    detail['scope']+='; projected legacy counters do not describe unchanged current shop geometry'
    return projected,m,[],detail

def _assert_close(actual,wanted,label,errors):
    try:
        a=np.asarray(actual,dtype=float);b=np.asarray(wanted,dtype=float)
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.allclose(a,b,rtol=0,atol=1e-9):raise ValueError()
    except (ValueError,TypeError):errors.append(dict(reason='Local/world transform mismatch',target=label))


def _audit_route_transform(local,world,P,label,errors):
    """World route points/servicePoint are transformed; centerline stays local."""
    _assert_close(world.get('points'),[P(p) for p in local['points']],label+'/points',errors)
    if len(local['points'])<2:errors.append(dict(reason='Access route needs at least two points',target=label))
    if 'centerline' in world:errors.append(dict(reason='World route retains redundant local centerline',target=label))
    if ('servicePoint' in local)!=('servicePoint' in world):errors.append(dict(reason='Local/world servicePoint presence mismatch',target=label))
    elif 'servicePoint' in local:_assert_close(world['servicePoint'],P(local['servicePoint']),label+'/servicePoint',errors)
    coordinate_fields={'points','centerline','servicePoint'}
    if {k:v for k,v in local.items() if k not in coordinate_fields}!={k:v for k,v in world.items() if k not in coordinate_fields}:
        errors.append(dict(reason='Local/world non-coordinate route descriptor changed',target=label))

def audit_metadata(manifest,*,before=None):
    """Review-time scope proof. New architecture is NOT frozen by this check."""
    before=before or load_before();old=before['manifest'];errors=[];info=manifest.get('shopPersonality',{})
    if not enabled(manifest):errors.append(dict(reason='features.shop_personality must be literal true'))
    if not isinstance(info,dict) or type(info.get('schema')) is not int or info.get('schema')!=SCHEMA or info.get('version')!=VERSION or info.get('baselineVersion')!='2.15.0':
        return False,dict(errors=errors+[dict(reason='Missing versioned shopPersonality manifest')])
    expected_top=set(before['manifestKeys'])|{'shopPersonality'}
    if set(manifest)!=expected_top:errors.append(dict(reason='Unapproved top-level manifest field change',missing=sorted(expected_top-set(manifest)),extra=sorted(set(manifest)-expected_top)))
    for name,sha in before['manifestFieldHashes'].items():
        if name not in manifest or digest(manifest[name])!=sha:errors.append(dict(reason='Unrelated manifest field changed',field=name))
    features=dict(old['features'],**{FEATURE:True})
    if manifest.get('features')!=features:errors.append(dict(reason='Other feature states changed'))
    if manifest.get('version')!=VERSION:errors.append(dict(reason='Unexpected revision version'))
    shops=info.get('shops');shops=shops if isinstance(shops,list) else []
    if [s.get('id') for s in shops]!=list(SHOPS):errors.append(dict(reason='Exactly eight ordered shop IDs required'))
    materials=manifest.get('materials',[]);base_m=old['materials'];base_names={r['name'] for r in base_m}
    originals=[m for m in materials if m.get('name') in base_names]
    if len(originals)!=len(base_m) or {m.get('name'):m for m in originals}!={m['name']:m for m in base_m}:errors.append(dict(reason='Original material descriptors missing, duplicated, or changed'))
    new_m=[m for m in materials if m.get('name') not in base_names];new_names=[r.get('name') for r in new_m]
    if len(new_names)!=len(set(new_names)) or any(not isinstance(n,str) or not n.startswith(('Food_','Night_')) or n in base_names for n in new_names):errors.append(dict(reason='Invalid private added material roster'))
    seats=manifest.get('stations',[]);old_seats=old['stations'];seat_names=[r.get('name') for r in seats]
    if seat_names!=[r['name'] for r in old_seats]:errors.append(dict(reason='49 original station IDs/order must remain'))
    for a,b in zip(old_seats,seats):
        if {k:v for k,v in a.items() if k not in ('position','exit','forward')}!={k:v for k,v in b.items() if k not in ('position','exit','forward')}:errors.append(dict(reason='Unapproved station field change',name=a['name']))
    all_lights=[];all_solids=[];all_stations=[];all_steam=[];owned_indices=[];routes_count=0
    frames={s['id']:s for s in before['layout']}
    for shop in shops:
        sid=shop.get('id');local=shop.get('local',{});world=shop.get('world',{});frame=shop.get('frame',{});layout=frames.get(sid)
        if layout is None:continue
        try:
            a=math.radians(layout['front_deg']);right=np.array([math.sin(a),-math.cos(a),0]);front=np.array([math.cos(a),math.sin(a),0]);up=np.array([0,0,1]);origin=np.array([layout['x'],layout['y'],layout['z']+100]);axes=np.array([right,front,up]);floor=origin[2]
            for name,value in [('right',right),('front',front),('up',up),('origin',origin)]:_assert_close(frame.get(name),value,sid+'/frame/'+name,errors)
            if frame.get('floorZ')!=floor:errors.append(dict(reason='Shop floor changed',shop=sid))
            P=lambda p:origin+np.asarray(p)@axes
            L=local.get('stations',[]);W=world.get('stations',[])
            if len(L)!=SEAT_COUNTS[SHOPS.index(sid)] or len(W)!=len(L):errors.append(dict(reason='Per-shop station count mismatch',shop=sid))
            for l,w in zip(L,W):
                if l.get('id')!=w.get('name') or w.get('shop')!=sid:errors.append(dict(reason='Local/world station ID mismatch',shop=sid))
                for field in ('position','exit'):_assert_close(w.get(field),P(l[field]),sid+'/'+str(l.get('id'))+'/'+field,errors)
                _assert_close(w.get('forward'),np.asarray(l['forward'])@axes,sid+'/'+str(l.get('id'))+'/forward',errors)
                v=np.asarray(w['forward'],float)
                if abs(np.linalg.norm(v)-1)>1e-9 or abs(v[2])>1e-9:errors.append(dict(reason='Station forward must be finite horizontal unit vector',shop=sid))
            all_stations.extend(W)
            L=local.get('solids',[]);W=world.get('solidBoxes',[])
            if len(L)!=len(W):errors.append(dict(reason='Local/world solid count mismatch',shop=sid))
            for l,w in zip(L,W):
                if w.get('name')!=sid+'_Personality_'+l.get('name',''):errors.append(dict(reason='Solid name is not exact owned local name',shop=sid))
                _assert_close(w.get('center'),P(l['center']),sid+'/'+w.get('name','')+'/center',errors)
                _assert_close(w.get('size'),l['size'],sid+'/'+w.get('name','')+'/size',errors)
                yaw=math.radians(l.get('yaw',0));rot=np.array([[math.cos(yaw),math.sin(yaw),0],[-math.sin(yaw),math.cos(yaw),0],[0,0,1]])
                _assert_close(w.get('axes'),(rot@axes).reshape(-1),sid+'/'+w.get('name','')+'/axes',errors)
                if any(v<=0 for v in l['size']):errors.append(dict(reason='Solid extent must be positive',shop=sid))
            all_solids.extend(W)
            L=local.get('routes',[]);W=world.get('routes',[]);routes_count+=len(W)
            if len(L)!=len(W) or not W:errors.append(dict(reason='Missing local/world named access routes',shop=sid))
            if len({r.get('name') for r in W})!=len(W):errors.append(dict(reason='Duplicate route names',shop=sid))
            for l,w in zip(L,W):
                _audit_route_transform(l,w,P,sid+'/'+str(l.get('name'))+'/route',errors)
            L=local.get('lights',[]);W=world.get('lights',[]);indices=world.get('lightIndices',[])
            if len(L)!=len(W) or len(W)!=len(indices):errors.append(dict(reason='Local/world light/index count mismatch',shop=sid))
            for l,w in zip(L,W):
                _assert_close(w.get('position'),P(l['position']),sid+'/light',errors)
                if {k:v for k,v in l.items() if k!='position'}!={k:v for k,v in w.items() if k!='position'}:errors.append(dict(reason='Light descriptor changed during transform',shop=sid))
            owned_indices.extend(indices);all_lights.extend(W)
            L=local.get('steam',[]);W=world.get('steam',[])
            if sid in NIGHTLIFE and (L or W):errors.append(dict(reason='Nightlife must not inherit food steam',shop=sid))
            if len(L)!=len(W):errors.append(dict(reason='Local/world steam count mismatch',shop=sid))
            for index,(l,w) in enumerate(zip(L,W)):
                pos=l.get('position') if isinstance(l,dict) else l
                _assert_close(w.get('position'),P(pos),sid+'/steam',errors)
                if w.get('id')!=(sid if index==0 else sid+'_Steam_'+str(index+1)):errors.append(dict(reason='Steam ID not owned by its shop',shop=sid))
            all_steam.extend(W)
        except (KeyError,ValueError,TypeError) as exc:errors.append(dict(reason='Invalid shop manifest record',shop=sid,error=str(exc)))
    if all_stations!=seats:errors.append(dict(reason='Global stations differ from explicit world shop records'))
    names=[r.get('name') for r in all_solids]
    if len(names)!=len(set(names)):errors.append(dict(reason='Duplicate owned solid names'))
    solids=manifest.get('solidBoxes',[]);owned=set(names);old_owned={s+'_solid' for s in SHOPS}
    if [r for r in solids if r.get('name') not in owned]!=[r for r in old['solidBoxes'] if r.get('name') not in old_owned]:errors.append(dict(reason='Five unrelated solid records changed or legacy shop solids remain'))
    if [r for r in solids if r.get('name') in owned]!=all_solids:errors.append(dict(reason='Global solid boxes differ from explicit owned records'))
    lights=manifest.get('lights',[])
    if (len(set(owned_indices))!=len(owned_indices) or any(type(i) is not int or i<0 or i>=len(lights) for i in owned_indices)):
        errors.append(dict(reason='Invalid explicit owned light indices'))
    else:
        if [lights[i] for i in owned_indices]!=all_lights:errors.append(dict(reason='World light records do not match global indexed entries'))
        if [l for i,l in enumerate(lights) if i not in set(owned_indices)]!=[l for i,l in enumerate(old['lights']) if i not in set(before['shopLightIndices'])]:errors.append(dict(reason='359 unrelated ordered light records changed'))
    if manifest.get('steam')!=all_steam:errors.append(dict(reason='Global steam differs from exact food-only world records'))
    unused=manifest.get('meshOptimization',{}).get('unused',{});prior=old['meshOptimization']['unused'];old_shop=set(map(tuple,before['shopKeys']))
    new_shop={('Shops/'+sid+'/Personality') for sid in SHOPS}
    def is_owned(row):return key(row) in old_shop or any(row.get('group','').startswith(p+'/') or row.get('group')==p for p in new_shop)
    if [r for r in unused.get('batches',[]) if not is_owned(r)]!=[r for r in prior['batches'] if not is_owned(r)]:errors.append(dict(reason='Unrelated unused-vertex optimization metadata changed'))
    for field in ('sea','cityCaps'):
        expected=copy.deepcopy(old['meshOptimization'][field])
        if field=='cityCaps':
            from shop_profile_contract import PROFILE_SHA256
            # Current final shop profile is an exact separately reviewed addition.
            # Trial diagnostics may still carry the complete old profile claim.
            actual_sha=manifest.get('meshOptimization',{}).get(field,{}).get('fantasyProfileSha256')
            if actual_sha==PROFILE_SHA256:expected['fantasyProfileSha256']=PROFILE_SHA256
        if manifest.get('meshOptimization',{}).get(field)!=expected:errors.append(dict(reason='Unrelated optimization metadata changed',field=field))
    altitude=manifest.get('altitudeProfile',{});old_altitude=old['altitudeProfile']
    for field,value in old_altitude.items():
        if field in ('visuals','metadataPositions','boxColliders'):continue
        if altitude.get(field)!=value:errors.append(dict(reason='Unrelated altitude policy/collision field changed',field=field))
    visual=altitude.get('visuals',{});old_visual=old_altitude['visuals']
    for field in ('retiledVertices','excludedBatches'):
        if visual.get(field)!=old_visual[field]:errors.append(dict(reason='Unrelated altitude visual counter changed',field=field))
    if visual.get('transformedBatches')!=old_visual['transformedBatches']+manifest.get('visualMeshCount',0)-old['visualMeshCount']:errors.append(dict(reason='Altitude transformed batch count does not match actual shop delta'))
    if altitude.get('boxColliders')!=len(solids):errors.append(dict(reason='Altitude box count does not equal current explicit boxes'))
    expected_positions=old_altitude['metadataPositions']+len(lights)-len(old['lights'])+len(all_steam)-len(old['steam'])+len(solids)-len(old['solidBoxes'])
    if altitude.get('metadataPositions')!=expected_positions:errors.append(dict(reason='Altitude metadata position count does not match explicit shop deltas',expected=expected_positions))
    return not errors,dict(errors=errors,actualStations=len(seats),actualShopSolids=len(all_solids),actualUnrelatedSolids=len(solids)-len(all_solids),actualShopLights=len(all_lights),actualUnrelatedLights=len(lights)-len(all_lights),actualSteam=len(all_steam),authoredShopRoutes=routes_count,scope='Proposal scope and local/world consistency only; new visual and metadata values not yet approved by this check')

def validate_metadata(manifest,*,oracle=None,before=None):
    import rpg_identity_contract as rpg
    if rpg.requested(manifest):
        ok,detail=rpg.validate_metadata(manifest)
        if not ok:return ok,detail
        prior=rpg.load_before()
        ok,old_detail=validate_metadata(prior['manifest'],oracle=oracle,before=before)
        detail['priorShopMetadata']=old_detail
        if not ok:detail['errors'].extend(old_detail['errors'])
        detail['passed']=not detail['errors'];return detail['passed'],detail
    before=before or load_before();oracle=oracle or load_oracle();ok,detail=audit_metadata(manifest,before=before)
    for name,sha in oracle['manifestFieldHashes'].items():
        if name not in manifest or digest(manifest[name])!=sha:detail['errors'].append(dict(reason='Approved manifest field differs from frozen value',field=name))
    detail['passed']=not detail['errors'];return detail['passed'],detail

def verify_dependencies(root,before=None,manifest=None):
    before=before or load_before();errors=[]
    if manifest is None:manifest=json.loads((Path(root)/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    for rel,sha in before['dependencies'].items():
        path=Path(root)/rel
        actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual==sha:continue
        if rel=='Assets/TreeTopYokocho/Data/FantasyMaterials.json' and enabled(manifest):
            try:
                from shop_profile_contract import verify_profile
                verify_profile(root);continue
            except (ValueError,OSError,KeyError,TypeError):pass
        errors.append(dict(reason='Unrelated render/layout dependency changed',path=rel))
    return not errors,dict(errors=errors,verifiedFiles=len(before['dependencies'])-len(errors))

def validate_native(root,manifest,batches=None,*,check_dependencies=True):
    import rpg_identity_contract as rpg
    if rpg.requested(manifest):return rpg.validate_native(root,manifest,batches,check_dependencies=check_dependencies)
    from peer_culling_contract import read_visual,summarize
    before=load_before(root);oracle=load_oracle(root)
    if batches is None:batches=read_visual(Path(root)/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes')
    ok,detail=validate_summaries([summarize(b) for b in batches],manifest,oracle=oracle,before=before)
    metadata_ok,metadata=validate_metadata(manifest,oracle=oracle,before=before);detail['metadata']=metadata
    old=before['manifest'];new_uv=manifest.get('normalUvRepairs');new_unused=manifest.get('meshOptimization',{}).get('unused',{}).get('removedVertices')
    if type(new_uv) is not int or new_uv<0 or type(new_unused) is not int or new_unused<0:
        metadata_ok=False;metadata['errors'].append(dict(reason='Invalid UV-repair/unused-vertex count'))
    else:
        expected=old['altitudeProfile']['visuals']['transformedVertices']+sum(len(b['vertices']) for b in batches)-sum(r['vertices'] for r in before['rows'])+new_unused-old['meshOptimization']['unused']['removedVertices']-3*(new_uv-old['normalUvRepairs'])
        if manifest.get('altitudeProfile',{}).get('visuals',{}).get('transformedVertices')!=expected:
            metadata_ok=False;metadata['errors'].append(dict(reason='Altitude transformed vertices do not match actual native/UV/compaction shop delta',expected=expected))

    collision=Path(root)/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes'
    collision_ok=collision.is_file() and hashlib.sha256(collision.read_bytes()).hexdigest()==before['collisionSha256']
    detail['unchangedCollisionMesh']=collision_ok
    dep_ok=True
    if check_dependencies:
        dep_ok,detail['dependencies']=verify_dependencies(root,before,manifest)
        for rel,sha in oracle['dependencies'].items():
            path=Path(root)/rel
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
                dep_ok=False;detail['dependencies']['errors'].append(dict(reason='Approved shop appearance/source dependency changed',path=rel))
    detail['passed']=ok and metadata_ok and collision_ok and dep_ok
    return detail['passed'],detail
