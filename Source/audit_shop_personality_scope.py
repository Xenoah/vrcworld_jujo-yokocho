"""Independent staging audit; preservation PASS never implies design approval."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def audit(project,*,strict=False):
    import shop_personality_contract as contract
    from peer_culling_contract import read_visual,summarize
    data=project/'Assets/TreeTopYokocho/Data';manifest=json.loads((data/'WorldManifest.json').read_text())
    import rpg_identity_contract as rpg
    if rpg.requested(manifest):
        from audit_rpg_identity_scope import audit as rpg_audit
        return rpg_audit(project,strict=strict)
    raw=(data/'VisualMeshes.bytes').read_bytes();batches=read_visual(data/'VisualMeshes.bytes');rows=[summarize(b) for b in batches]
    before=contract.load_before();old_keys=set(map(tuple,before['shopKeys']));old_nonshop=[r for r in before['rows'] if contract.key(r) not in old_keys];nonshop_keys={contract.key(r) for r in old_nonshop}
    errors=contract._actual_count_errors(rows,manifest)+contract.validate_gate(manifest);scope='baseline' if not contract.enabled(manifest) else 'proposal'
    actual_nonshop=[r for r in rows if contract.key(r) in nonshop_keys]
    errors.extend(contract._rows_errors(actual_nonshop,old_nonshop))
    new_rows=[r for r in rows if contract.key(r) not in nonshop_keys]
    if scope=='baseline':
        if hashlib.sha256(raw).hexdigest()!=contract.BEFORE_NATIVE_SHA256:errors.append(dict(reason='Feature-absent world is not the exact baseline'))
        if 'shopPersonality' in manifest:errors.append(dict(reason='Metadata present without literal feature'))
        metadata=dict(status='BASELINE',actualStations=len(manifest['stations']),actualSolids=len(manifest['solidBoxes']))
    else:
        prefixes=tuple('Shops/'+sid+'/Personality/' for sid in contract.SHOPS)
        retained=contract.load_retained();retained_keys={contract.key(r) for r in retained}
        errors.extend(contract._rows_errors([r for r in new_rows if contract.key(r) in retained_keys],retained))
        unowned=[contract.key(r) for r in new_rows if contract.key(r) not in retained_keys and not r['group'].startswith(prefixes)]
        if unowned:errors.append(dict(reason='Unapproved proposal ownership or legacy shop branch retained',keys=unowned))
        counts={sid:sum(r['group'].startswith('Shops/'+sid+'/Personality/') for r in new_rows) for sid in contract.SHOPS}
        if any(v==0 for v in counts.values()):errors.append(dict(reason='Each of eight shops needs replacement records',counts=counts))
        keys=[contract.key(r) for r in new_rows]
        if len(keys)!=len(set(keys)):errors.append(dict(reason='Duplicate proposed shop native records'))
        ok,metadata=contract.audit_metadata(manifest,before=before);errors.extend(metadata['errors'])
    dep_ok,dependencies=contract.verify_dependencies(project,before);errors.extend(dependencies['errors'])
    collision=(data/'CollisionMeshes.bytes').read_bytes();collision_sha=hashlib.sha256(collision).hexdigest()
    if collision_sha!=before['collisionSha256']:errors.append(dict(reason='Physical floor/ramp/barrier native payload changed'))
    approved=False
    if strict:
        try:
            approved,native=contract.validate_native(project,manifest,batches)
            if not approved:errors.append(dict(reason='Frozen approved admission failed',detail=native))
        except (OSError,ValueError) as exc:errors.append(dict(reason=str(exc)))
    changed=[r for r in rows if contract.key(r) in nonshop_keys and r not in old_nonshop]
    return dict(status='FAIL' if errors else ('PASS_FROZEN_ADMISSION' if approved else 'PASS_PRESERVATION_ONLY'),
                designAccepted=approved,scope=scope,errors=errors,
                actualNativeSha256=hashlib.sha256(raw).hexdigest(),beforeNativeSha256=contract.BEFORE_NATIVE_SHA256,
                actualNativeBatches=len(rows),actualNativeVertices=sum(r['vertices'] for r in rows),actualNativeTriangles=sum(r['triangles'] for r in rows),
                expectedNonshopBatches=len(old_nonshop),actualNonshopBatches=len(actual_nonshop),exactPreservedNonshopBatches=len(actual_nonshop)-len(changed),
                oldShopBatches=len(old_keys),actualShopBatches=len(new_rows),collisionSha256=collision_sha,
                metadata=metadata,dependencies=dependencies,
                limitations='This compares actual payloads before normalization. A preservation-only result does not approve architecture or route usability. Unity and VRChat runtime unavailable.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True);parser.add_argument('--strict',action='store_true');parser.add_argument('--report',type=Path);args=parser.parse_args()
    sys.path.append(str(args.project/'Source'));result=audit(args.project,strict=args.strict)
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));return bool(result['errors'])
if __name__=='__main__':raise SystemExit(main())
