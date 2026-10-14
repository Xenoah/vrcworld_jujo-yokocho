"""Test-only exact inverse. Invoke before the unchanged original 132-batch inverse."""
import hashlib,io,copy
from pathlib import Path
import numpy as np
from city_roof_caps import KEY,FEATURE
from city_roof_caps_contract import load_oracle
from peer_culling_contract import summarize
INVERSE_SHA256='07dc545b9df2979c74baa3f0e4e1b1e2f851ce90b8582ece7a17e9b6e16d701a'
def restore_city_caps(batches,manifest):
    pin=load_oracle();raw=(Path(__file__).resolve().parent/'testdata/city_roof_caps_inverse_2_15.npz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=INVERSE_SHA256:raise ValueError('City cap inverse fixture changed')
    out=[]
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        for b in batches:
            if (b['group'],b['material'])!=KEY:out.append(b);continue
            actual=summarize(b)
            if actual==pin['before']:out.append(b);continue
            if actual!=pin['after']:raise ValueError('Cannot invert unapproved city cap payload')
            restored=dict(b,**{a:archive[a].copy() for a in ('vertices','uv','colors','faces')})
            if summarize(restored)!=pin['before']:raise ValueError('City cap inverse differs from original')
            out.append(restored)
    if sum((b['group'],b['material'])==KEY for b in out)!=1:raise ValueError('City cap batch roster changed')
    m=copy.deepcopy(manifest);m['features'].pop(FEATURE,None)
    if isinstance(m.get('meshOptimization'),dict):m['meshOptimization'].pop('cityCaps',None)
    m['visualTriangles']=sum(len(b['faces']) for b in out)
    return out,m
