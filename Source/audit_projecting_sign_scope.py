"""Current additive preservation diagnostics, separate from art acceptance."""
import json
from pathlib import Path
import projecting_sign_contract as c

def audit(root,*,strict=False):
    import rpg_identity_contract as rpg
    import s05_pendant_contract as prior_contract
    from peer_culling_contract import read_visual
    from projecting_sign_geometry_scope import audit as geometry_audit
    root=Path(root);data=root/'Assets/TreeTopYokocho/Data';m=json.loads((data/'WorldManifest.json').read_text());batches=read_visual(data/'VisualMeshes.bytes');rows=rpg.summarize_batches(batches)
    old=c.before();_,scope=c.audit_scope(rows,m,prior=old);errors=list(scope['errors'])
    if errors:return dict(status='FAIL',designAccepted=False,errors=errors,scope=scope)
    geometry=geometry_audit(batches,m);errors.extend(geometry['errors'])
    prior=prior_contract.load_oracle()
    for rel,expected in prior['dependencies'].items():
        if rel in c.SOURCE_CHANGES:continue
        p=root/rel
        if not p.is_file() or c.sha(p.read_bytes())!=expected:errors.append(dict(reason='Immutable v2.18 source/runtime/texture dependency changed',path=rel))
    if m[c.METADATA]['sourceSha256']!=c.sha((root/c.NEW_SOURCES[0]).read_bytes()):errors.append(dict(reason='Actual added module source differs from declared sign provenance'))
    for prefix in ('Assets/TreeTopYokocho/Textures/','Source/fonts/'):
        actual={str(p.relative_to(root)) for p in (root/prefix).rglob('*') if p.is_file() and p.suffix!='.meta'}
        if actual!={p for p in prior['dependencies'] if p.startswith(prefix)}:errors.append(dict(reason='Immutable texture/font roster changed',path=prefix))
    if c.sha((data/'CollisionMeshes.bytes').read_bytes())!=old['collisionSha256']:errors.append(dict(reason='Immutable collision bytes changed'))
    from rpg_runtime_compatibility import verify_runtime
    try:verify_runtime(root)
    except (ValueError,OSError,KeyError,TypeError) as e:errors.append(dict(reason=str(e)))
    approved=False;native=None
    if strict:
        approved,native=c.validate_native(root,m,batches)
        if not approved:errors.extend(native['errors'])
    return dict(status='FAIL' if errors else ('PASS_FROZEN_ADMISSION' if approved else 'PASS_PRESERVATION_ONLY'),designAccepted=approved,errors=errors,scope=scope,geometry=geometry,nativeAdmission=native,actualNativeSha256=c.sha((data/'VisualMeshes.bytes').read_bytes()),beforeNativeSha256=c.BEFORE_NATIVE_SHA256,actualNativeBatches=len(rows),actualNativeTriangles=sum(r['triangles'] for r in rows),limitations='Exact old geometry/metadata/source preservation and shape diagnostics only unless independently accepted after checkpoint is frozen. No Unity/VRChat/bake/runtime claim.')
