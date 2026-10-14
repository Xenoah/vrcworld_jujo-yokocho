"""TEST ONLY: selected exact-12 inverse, never production admission.

Compose before city-cap inverse and original 132 inverse/full-world SHA.
Restores both geometry and soft snow directly to the original prior arrays.
"""
import copy,hashlib,io
from pathlib import Path
import numpy as np
import mountain_quality_contract as contract
from mountain_detail_test_fixture import frozen_arrays as detail_arrays
ARRAY_NAME='mountain_quality_arrays_v2.npz'
ARRAY_SHA256='b8bf8e73c941d9465d0a6d49bae614c9cc2f7f37bdf6561d0a86111868d59913'


def selected_arrays():
    from peer_culling_contract import summarize
    raw=(Path(__file__).resolve().parent/'testdata'/ARRAY_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ARRAY_SHA256:raise ValueError('Frozen selected mountain arrays changed')
    result=[];oracle=contract.load_oracle()
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        for i,(group,material) in enumerate(contract.KEYS):
            b={'group':group,'material':material}
            for field in ('vertices','uv','colors','faces'):b[field]=archive[f'selected_{i}_{field}'].copy()
            if summarize(b)!=oracle['selected'][i]:raise ValueError('Selected arrays differ from frozen summary')
            result.append(b)
    return result


def restore_prior_mountains(batches,manifest):
    features=manifest.get('features',{});adaptive,snow,craft,normals=contract.flags(features)
    result=contract.validate_native_mountains(batches,features)
    if not result['passed']:raise ValueError(str(result['errors']))
    if not adaptive:return batches,manifest
    baseline={(b['group'],b['material']):b for b in detail_arrays('before_snow' if snow else 'before_plain')}
    out=[baseline.get((b['group'],b['material']),b) for b in batches]
    m=copy.deepcopy(manifest)
    for feature in ('mountain_detail','mountain_snow_craft','mountain_seam_normals'):m['features'].pop(feature,None)
    for field in ('mountainDetail','mountainSnowCraft','mountainSeamNormals'):m.pop(field,None)
    m['visualTriangles']=sum(len(b['faces']) for b in out);m['visualMeshCount']=len(out)
    if 'detail' in m and 'landscapeTriangles' in m['detail']:m['detail']['landscapeTriangles']-=3756
    return out,m
