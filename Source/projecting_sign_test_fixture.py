"""TEST ONLY exact additive inverse to d0386d before unchanged S05/RPG chain."""
import copy
import projecting_sign_contract as c

def restore_prior_projecting_signs(batches,manifest):
    if not c.requested(manifest):return batches,manifest
    import rpg_identity_contract as rpg
    from visual_optimization_test_fixture import native_sha
    ok,report=c.validate_summaries(rpg.summarize_batches(batches),manifest)
    if not ok:raise ValueError('Cannot invert unapproved sign native/metadata: '+str(report['errors']))
    remove=set(c.KEYS);out=[b for b in batches if c.key(b) not in remove]
    if len(out)!=len(batches)-len(remove) or native_sha(out)!=c.BEFORE_NATIVE_SHA256:raise ValueError('Whole sign-restored native must equal exact accepted v2.18 d0386d')
    return out,copy.deepcopy(c.before()['manifest'])
