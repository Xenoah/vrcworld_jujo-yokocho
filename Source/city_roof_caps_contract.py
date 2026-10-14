"""One exact batch revision. Normalize only authenticated payloads, never families."""
import hashlib,json,copy
from pathlib import Path
from city_roof_caps import KEY,FEATURE
ORACLE_NAME='city_roof_caps_2_15.json'
ORACLE_SHA256='b62988d6ebf06b9a139be864530dc66d7899ec03b4cc786a0347adc4e4cf9b37'
SURFACE_SHA256='257f7182ecae848076849b1e3da32aa46aa2c583515d582139aaac8b54a0ea29'
BUILDER_SHA256='b1457615342413a2f099308920883169ec5aec88c39b932511a4e8fd0a10c119'
PROFILE_SHA256='6cf7669a43f2b45678057f22fcf344cc753b9b65b350e0c6b13700e3131f3c8e'
PROFILE_LOADER_SHA256='35c71226480ecf3e1e471bdf35d315e8304a636f227b8a1ffc2fc893a16baa5d'
FIELDS=('vertices','triangles','geometrySha256','attributesAndIndicesSha256')
def requested(manifest):
    f=manifest.get('features',{});return isinstance(f,dict) and FEATURE in f

def load_oracle(root=None):
    base=Path(root)/'Source' if root is not None else Path(__file__).resolve().parent
    raw=(base/'testdata'/ORACLE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORACLE_SHA256:raise ValueError('Frozen city cap oracle changed')
    data=json.loads(raw)
    if any((data[k]['group'],data[k]['material'])!=KEY for k in ('before','after')):raise ValueError('Invalid cap roster')
    return data

def verified_dependencies(root, *, shop_personality=False):
    if type(shop_personality) is not bool:raise ValueError('City cap shop profile gate must be literal Boolean')
    profile_sha=PROFILE_SHA256
    if shop_personality:
        from shop_profile_contract import verify_profile
        profile_sha=verify_profile(root)
    # Source compatibility is frozen before visual acceptance; never bypass art admission.
    from rpg_runtime_compatibility import approved_builder_sha
    builder_sha=approved_builder_sha(root)
    for rel,digest in [('Shaders/YokochoSurface.shader',SURFACE_SHA256),('Editor/YokochoWorldBuilder.cs',builder_sha),('Data/FantasyMaterials.json',profile_sha),('Editor/FantasyMaterialProfile.cs',PROFILE_LOADER_SHA256)]:
        if hashlib.sha256((Path(root)/'Assets/TreeTopYokocho'/rel).read_bytes()).hexdigest()!=digest:raise ValueError('City caps require reviewed opaque/static material and shadow routing: '+rel)
    return dict(surfaceShaderSha256=SURFACE_SHA256,builderSha256=builder_sha,fantasyProfileSha256=profile_sha,fantasyProfileLoaderSha256=PROFILE_LOADER_SHA256)

def normalize_summaries(summaries,manifest):
    if not requested(manifest):return summaries,manifest,[],None
    pin=load_oracle();active=manifest['features'].get(FEATURE) is True;expected=pin['after' if active else 'before'];errors=[]
    if manifest.get('visualMeshCount')!=len(summaries) or manifest.get('visualTriangles')!=sum(r['triangles'] for r in summaries):errors.append(dict(reason='City cap actual export count mismatch'))
    rows=[r for r in summaries if (r['group'],r['material'])==KEY]
    if len(rows)!=1 or any(rows[0].get(k)!=expected[k] for k in FIELDS):errors.append(dict(reason='Exact city cap payload mismatch',feature=active))
    if active:
        profile_sha=PROFILE_SHA256
        if manifest.get('features',{}).get('shop_personality') is True:
            from shop_profile_contract import PROFILE_SHA256 as profile_sha
        metadata=manifest.get('meshOptimization',{});metadata=metadata.get('cityCaps',{}) if isinstance(metadata,dict) else {};metadata=metadata if isinstance(metadata,dict) else {}
        if any(metadata.get(k)!=v for k,v in dict(surfaceShaderSha256=SURFACE_SHA256,builderSha256=BUILDER_SHA256,fantasyProfileSha256=profile_sha,fantasyProfileLoaderSha256=PROFILE_LOADER_SHA256).items()):errors.append(dict(reason='City cap render dependency mismatch'))
        materials=manifest.get('materials',[])
        matching=[m for m in materials if isinstance(m,dict) and m.get('name')=='DarkTimber'] if isinstance(materials,list) else []
        if matching!=[pin['material']]:errors.append(dict(reason='City cap opaque DarkTimber descriptor changed'))
    if errors:return summaries,manifest,errors,None
    out=[dict(r,**{f:pin['before'][f] for f in FIELDS}) if active and (r['group'],r['material'])==KEY else r for r in summaries]
    m=dict(manifest);m['visualTriangles']=sum(r['triangles'] for r in out)
    return out,m,[],dict(oracleSha256=ORACLE_SHA256,enabled=active,exactAdmittedBatches=int(active),enclosedCaps=834 if active else 0)
