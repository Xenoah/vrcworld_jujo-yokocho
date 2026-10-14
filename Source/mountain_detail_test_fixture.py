"""Test-only exact mountain inverse; NEVER use for production admission.

Compose this BEFORE visual_optimization_test_fixture.restored_prior_fixture.
That helper must still verify its original full-world native SHA unchanged.
"""
import copy,hashlib,io
from pathlib import Path
import numpy as np
import mountain_detail_contract as contract

ARRAY_NAME='mountain_detail_arrays_v1.npz'
ARRAY_SHA256='4ffff15a0d61d06cf02e7959726836a3aa397e1adc75dbd8e7adcbf7b387cdfd'


def frozen_arrays(variant):
    from peer_culling_contract import summarize
    raw=(Path(__file__).resolve().parent/'testdata'/ARRAY_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ARRAY_SHA256:raise ValueError('Frozen mountain array fixture changed')
    oracle=contract.load_oracle();result=[]
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        for i,(group,material) in enumerate(contract.KEYS):
            b={'group':group,'material':material}
            for field in ('vertices','uv','colors','faces'):b[field]=archive[f'{variant}_{i}_{field}'].copy()
            if summarize(b)!=oracle['variants'][variant][i]:raise ValueError('Frozen arrays do not match exact mountain summary')
            result.append(b)
    return result


def restore_prior_mountains(batches,manifest):
    """Undo this feature only; preserve unrelated arrays and old snow colors."""
    detail,snow=contract.flags(manifest.get('features',{}))
    result=contract.validate_native_mountains(batches,manifest.get('features',{}))
    if not result['passed']:raise ValueError(str(result['errors']))
    if not detail:return batches,manifest
    baseline={(b['group'],b['material']):b for b in frozen_arrays('before_snow' if snow else 'before_plain')}
    out=[baseline.get((b['group'],b['material']),b) for b in batches]
    m=copy.deepcopy(manifest);m['features'].pop(contract.FEATURE,None);m.pop('mountainDetail',None)
    m['visualTriangles']=sum(len(b['faces']) for b in out);m['visualMeshCount']=len(out)
    if 'detail' in m and 'landscapeTriangles' in m['detail']:m['detail']['landscapeTriangles']-=3756
    return out,m
