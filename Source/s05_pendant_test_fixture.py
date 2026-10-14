"""TEST ONLY exact v2.18 inverse to immutable104fe596 before old f52/d622 chain."""
import copy
import s05_pendant_contract as c

def restore_prior_pendant(batches,manifest):
    if not c.requested(manifest):return batches,manifest
    import rpg_identity_contract as rpg
    from s05_pendant_geometry_scope import old_pale
    from visual_optimization_test_fixture import native_sha
    ok,report=c.validate_summaries(rpg.summarize_batches(batches),manifest)
    if not ok:raise ValueError('Cannot invert unapproved S05 native/metadata: '+str(report['errors']))
    old=old_pale();out=[old if c.key(b)==c.OLD_KEY else b for b in batches if c.key(b)!=c.NEW_KEY]
    if native_sha(out)!=c.BEFORE_NATIVE_SHA256:raise ValueError('Whole S05-restored native must equal104fe596 v2.17 state11')
    return out,copy.deepcopy(c.before()['manifest'])
