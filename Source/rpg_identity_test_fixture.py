"""TEST ONLY: authenticate current art, restore exact f52, then old inverse chain."""
import copy
import io
from pathlib import Path
import numpy as np
import rpg_identity_contract as c
INVERSE_NAME='rpg_identity_inverse_2_17.npz'
INVERSE_SHA256='dcb921791107b3ee80dc9999d25ad2034e32f9a508ceaae66484ba7d809e24e6'

def restore_prior_identity(batches,manifest):
    from projecting_sign_test_fixture import restore_prior_projecting_signs
    batches,manifest=restore_prior_projecting_signs(batches,manifest)
    from s05_pendant_test_fixture import restore_prior_pendant
    batches,manifest=restore_prior_pendant(batches,manifest)
    if not c.requested(manifest):return batches,manifest
    rows=c.summarize_batches(batches)
    ok,detail=c.validate_summaries(rows,manifest)
    if not ok:raise ValueError('Cannot invert unapproved RPG payload: '+str(detail['errors']))
    before=c.load_before();scope,report=c.audit_scope(rows,manifest,before=before)
    if not scope:raise ValueError('Cannot invert out-of-scope RPG payload: '+str(report['errors']))
    raw=(Path(__file__).resolve().parent/'testdata'/INVERSE_NAME).read_bytes()
    if c.sha(raw)!=INVERSE_SHA256:raise ValueError('Immutable sign UV inverse changed')
    signs=set(map(tuple,before['signKeys']));out=[]
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        for index,(row,batch) in enumerate(zip(before['rows'],batches)):
            b=dict(batch);b['group']=row['group'];b['material']=row['material']
            if c.key(row) in signs:b['uv']=archive[str(index)+'_uv'].copy()
            out.append(b)
    from visual_optimization_test_fixture import native_sha
    if native_sha(out)!=c.BEFORE_NATIVE_SHA256:raise ValueError('Whole RPG-restored native must equal immutable f52 v2.16')
    return out,copy.deepcopy(before['manifest'])
