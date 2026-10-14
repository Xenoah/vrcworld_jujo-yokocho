"""Current S05 preservation diagnostics; never self-approve new art."""
import json
from pathlib import Path
import s05_pendant_contract as c

def audit(root,*,strict=False):
    import rpg_identity_contract as rpg
    from peer_culling_contract import read_visual
    from rpg_runtime_compatibility import verify_runtime
    from s05_pendant_geometry_scope import audit as geometry_audit
    root=Path(root);data=root/'Assets/TreeTopYokocho/Data';m=json.loads((data/'WorldManifest.json').read_text())
    batches=read_visual(data/'VisualMeshes.bytes');rows=rpg.summarize_batches(batches);prior=c.before()
    ok,scope=c.audit_scope(rows,m,prior=prior);errors=list(scope['errors'])
    if errors:return dict(status='FAIL',designAccepted=False,errors=errors,scope=scope)
    geometry=geometry_audit(batches,m);errors.extend(geometry['errors'])
    for rel,expected in prior['dependencies'].items():
        if rel in c.SOURCE_CHANGES:continue
        p=root/rel
        if not p.is_file() or c.sha(p.read_bytes())!=expected:errors.append(dict(reason='Unrelated immutable v2.17 dependency changed',path=rel))
    try:verify_runtime(root)
    except (ValueError,OSError,KeyError,TypeError) as e:errors.append(dict(reason=str(e)))
    if c.sha((data/'CollisionMeshes.bytes').read_bytes())!=rpg.load_before()['collisionSha256']:errors.append(dict(reason='Immutable collision bytes changed'))
    for prefix in ('Assets/TreeTopYokocho/Textures/','Source/fonts/'):
        actual={str(p.relative_to(root)) for p in (root/prefix).rglob('*') if p.is_file() and p.suffix!='.meta'}
        if actual!={p for p in prior['dependencies'] if p.startswith(prefix)}:errors.append(dict(reason='Immutable texture/font roster changed',path=prefix))
    for shop in m['shopPersonality']['shops']:
        if shop['sourceSha256']!=c.sha((root/'Source'/(shop['module']+'.py')).read_bytes()):errors.append(dict(reason='Actual shop source provenance mismatch',shop=shop['id']))
    approved=False;native=None
    if strict:
        approved,native=c.validate_native(root,m,batches)
        if not approved:errors.extend(native['errors'])
    return dict(status='FAIL' if errors else ('PASS_FROZEN_ADMISSION' if approved else 'PASS_PRESERVATION_ONLY'),designAccepted=approved,errors=errors,scope=scope,geometry=geometry,nativeAdmission=native,
        actualNativeSha256=c.sha((data/'VisualMeshes.bytes').read_bytes()),beforeNativeSha256=c.BEFORE_NATIVE_SHA256,
        actualNativeBatches=len(rows),actualNativeTriangles=sum(r['triangles'] for r in rows),limitations='Preservation/shape proof only unless separately frozen art admission passes. No Unity/VRChat bake or runtime claim.')
