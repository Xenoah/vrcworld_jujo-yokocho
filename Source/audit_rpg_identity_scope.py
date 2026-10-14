"""Current RPG preservation diagnostics are distinct from frozen art admission."""
import json
from pathlib import Path
import rpg_identity_contract as c

def audit(root,*,strict=False):
    from peer_culling_contract import read_visual
    from rpg_runtime_compatibility import verify_runtime
    root=Path(root);data=root/'Assets/TreeTopYokocho/Data'
    m=json.loads((data/'WorldManifest.json').read_text())
    import projecting_sign_contract as signs
    if signs.requested(m):
        from audit_projecting_sign_scope import audit as sign_audit
        return sign_audit(root,strict=strict)
    import s05_pendant_contract as pendant
    if pendant.requested(m):
        from audit_s05_pendant_scope import audit as pendant_audit
        return pendant_audit(root,strict=strict)
    before=c.load_before()
    batches=read_visual(data/'VisualMeshes.bytes');rows=c.summarize_batches(batches)
    ok,scope=c.audit_scope(rows,m,before=before);errors=list(scope['errors'])
    if errors:return dict(status='FAIL',designAccepted=False,errors=errors,scope=scope)
    def check(value,reason,**kw):
        if not value:errors.append(dict(reason=reason,**kw))
    for rel,old in before['dependencies'].items():
        if rel in c.SOURCE_CHANGES or (m['features'][c.FLAGS[0]] and rel in c.ATLASES):continue
        path=root/rel
        check(path.is_file() and c.sha(path.read_bytes())==old,'Unrelated frozen dependency changed',path=rel)
    try:verify_runtime(root)
    except (ValueError,OSError,KeyError,TypeError) as e:errors.append(dict(reason=str(e)))
    check(c.sha((data/'CollisionMeshes.bytes').read_bytes())==before['collisionSha256'],'Immutable collision bytes changed')
    for shop in m['shopPersonality']['shops']:
        module={'S01':'food_venues.py','S02':'food_venues.py','S03':'food_venues.py','S04':'nightlife_venues.py','S05':'food_venues.py','S06':'nightlife_venues.py','S07':'nightlife_venues.py','S08':'food_venues.py'}[shop['id']]
        check(shop['sourceSha256']==c.sha((root/'Source'/module).read_bytes()),'Shop source provenance does not match current source',shop=shop['id'])
    if m['features'][c.FLAGS[0]]:
        info=m['shopRpgIdentity']
        check(info['sourceSha256']==c.sha((root/'Source/rpg_shop_identities.py').read_bytes()),'Identity source provenance mismatch')
        check(info['fontManifestSha256']==c.sha((root/'Source/fonts/rpg-fonts.json').read_bytes()),'Font manifest provenance mismatch')
        check(info['atlasSha256']=={Path(rel).name:c.sha((root/rel).read_bytes()) for rel in c.ATLASES},'Atlas provenance mismatch')
    try:
        import venue_lighting as lighting
        profile=lighting.load_profile(root/lighting.PROFILE_RELATIVE)
        lighting.validate_manifest(m,profile)
    except (ValueError,OSError,KeyError,TypeError) as e:errors.append(dict(reason=str(e)))
    approved=False;native=None
    if strict:
        approved,native=c.validate_native(root,m,batches)
        if not approved:errors.extend(native['errors'])
    return dict(status='FAIL' if errors else ('PASS_FROZEN_ADMISSION' if approved else 'PASS_PRESERVATION_ONLY'),designAccepted=approved,scope=scope,errors=errors,nativeAdmission=native,
        actualNativeSha256=c.sha((data/'VisualMeshes.bytes').read_bytes()),beforeNativeSha256=c.BEFORE_NATIVE_SHA256,
        actualNativeBatches=len(rows),actualNativeTriangles=sum(r['triangles'] for r in rows),
        limitations='Current exact payload preservation only unless frozen admission explicitly passes. No Unity/VRChat bake or runtime claim.')
