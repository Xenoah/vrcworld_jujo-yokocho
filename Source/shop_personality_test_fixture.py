"""TEST-ONLY exact native shop inverse; NEVER import from production admission.

Compose before mountain -> city caps -> original 132-batch inverse. The complete
shop-restored world must equal d812... before any later historical inverse runs.
"""
import copy
import hashlib
import io
from pathlib import Path
import numpy as np
import shop_personality_contract as contract

INVERSE_NAME='shop_personality_inverse_2_16.npz'
INVERSE_SHA256='7dd364125413c0a07ae53310f721e221f97ff7a2de920e4cdfdc27dce2c93c83'

def restore_prior_shops(batches,manifest):
    from rpg_identity_test_fixture import restore_prior_identity
    batches,manifest=restore_prior_identity(batches,manifest)
    errors=contract.validate_gate(manifest)
    if errors:raise ValueError(str(errors))
    if not contract.enabled(manifest):return batches,manifest
    from peer_culling_contract import summarize
    from visual_optimization_test_fixture import native_sha
    before=contract.load_before();oracle=contract.load_oracle()
    ok,report=contract.validate_summaries([summarize(b) for b in batches],manifest,oracle=oracle,before=before)
    if not ok:raise ValueError('Cannot invert unapproved shop payload: '+str(report['errors']))
    metadata_ok,metadata=contract.validate_metadata(manifest,oracle=oracle,before=before)
    if not metadata_ok:raise ValueError('Cannot invert unapproved shop metadata: '+str(metadata['errors']))
    raw=(Path(__file__).resolve().parent/'testdata'/INVERSE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=INVERSE_SHA256:raise ValueError('Frozen shop inverse arrays changed')
    restored={};old={contract.key(r):r for r in before['rows']}
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        for i,pair in enumerate(before['shopKeys']):
            k=tuple(pair);row={'group':k[0],'material':k[1]}
            for attr in ('vertices','uv','colors','faces'):row[attr]=archive[str(i)+'_'+attr].copy()
            if summarize(row)!=old[k]:raise ValueError('Restored shop record differs from independently frozen before payload')
            restored[k]=row
    actual={contract.key(b):b for b in batches}
    out=[restored[contract.key(r)] if contract.key(r) in restored else actual[contract.key(r)] for r in before['rows']]
    if native_sha(out)!=contract.BEFORE_NATIVE_SHA256:raise ValueError('Whole shop-restored native does not equal d812 baseline')
    m=copy.deepcopy(manifest)
    for name,value in before['manifest'].items():m[name]=copy.deepcopy(value)
    m.pop('shopPersonality',None)
    return out,m
