"""Collect four exact scope-checked variants. DOES NOT approve or freeze art.

A reviewer must compare this proposal with independently viewed source art and
explicitly approve its hash before the production ORACLE_SHA256 is updated.
"""
import argparse,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Source'))
import rpg_identity_contract as c
p=argparse.ArgumentParser();p.add_argument('--variants',type=Path,required=True,help='JSON map of 00/01/10/11 to built roots');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
roots=json.loads(a.variants.read_text())
if set(roots)!={'00','01','10','11'}:raise ValueError('Need four independently built literal variants')
sys.path.append(str(Path(roots['11'])/'Source'))
from peer_culling_contract import read_visual
from audit_rpg_identity_glb import audit
from rpg_runtime_compatibility import verify_runtime
before=c.load_before();variants={}
for state,location in sorted(roots.items()):
    root=Path(location);manifest=json.loads((root/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    if c.validate_gate(manifest) or c.variant_key(manifest)!=state:raise ValueError('Wrong literal variant: '+state)
    native=root/'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'
    rows=c.summarize_batches(read_visual(native));ok,scope=c.audit_scope(rows,manifest,before=before)
    if not ok:raise ValueError(json.dumps(scope))
    glb=audit(root,manifest)
    if glb['status']!='PASS':raise ValueError(json.dumps(glb))
    verify_runtime(root)
    import venue_lighting as lighting
    lighting.validate_manifest(manifest,lighting.load_profile(root/lighting.PROFILE_RELATIVE))
    for shop in manifest['shopPersonality']['shops']:
        if shop['sourceSha256']!=c.sha((root/'Source'/(shop['module']+'.py')).read_bytes()):raise ValueError('Shop source provenance mismatch')
    dependencies={}
    for rel,old in before['dependencies'].items():
        value=c.sha((root/rel).read_bytes());allowed=rel in c.SOURCE_CHANGES or (state[0]=='1' and rel in c.ATLASES)
        if not allowed and value!=old:raise ValueError('Unrelated immutable source/texture/oracle changed: '+rel)
        dependencies[rel]=value
    for rel in c.NEW_SOURCES:
        dependencies[rel]=c.sha((root/rel).read_bytes())
    for file in sorted((root/'Source/fonts').rglob('*')):
        if file.is_file():dependencies[str(file.relative_to(root))]=c.sha(file.read_bytes())
    actual_textures={str(p.relative_to(root)) for p in (root/'Assets/TreeTopYokocho/Textures').rglob('*') if p.is_file() and p.suffix!='.meta'}
    expected_textures={p for p in before['dependencies'] if p.startswith('Assets/TreeTopYokocho/Textures/')}
    if actual_textures!=expected_textures:raise ValueError('Texture file roster changed')
    if c.sha((root/'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes())!=before['collisionSha256']:raise ValueError('Collision bytes changed')
    if state[0]=='1':
        info=manifest['shopRpgIdentity']
        if info['sourceSha256']!=dependencies['Source/rpg_shop_identities.py'] or info['fontManifestSha256']!=dependencies['Source/fonts/rpg-fonts.json']:raise ValueError('Identity source provenance does not match actual files')
        if info['atlasSha256']!={Path(rel).name:dependencies[rel] for rel in c.ATLASES}:raise ValueError('Identity atlas provenance does not match actual files')
    variants[state]=dict(rows=rows,manifest=manifest,dependencies=dependencies,nativeSha256=c.sha(native.read_bytes()),glbSha256=glb['glbSha256'])
    print(state,'scope PASS',variants[state]['nativeSha256'],flush=True)
result=dict(schema=1,version=c.VERSION,beforeNativeSha256=c.BEFORE_NATIVE_SHA256,variants=variants)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_bytes(gzip.compress(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(),mtime=0))
print('PROPOSAL ONLY',c.sha(a.output.read_bytes()),a.output)
