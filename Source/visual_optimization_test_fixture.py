"""Test-only inverse fixture for legacy synthetic matrices; NEVER admission.

Restores reviewed unreferenced vertices and the original four planar sea grids
from independently frozen pre-change evidence. The WHOLE reconstructed v2.14
native SHA must match, not just its optimized batches. Production validation
uses actual after hashes and does not call this module.
"""
import hashlib,io,struct,copy
from pathlib import Path
import numpy as np
import peer_culling_contract as peer
import visual_optimization_contract as contract

INVERSE_NAME='visual_optimization_inverse_2_15.npz'
INVERSE_SHA256='11e162496ce0caad40a4622098e6b53478767d27b08996e4397e1d3a9d1981a8'
ORIGINAL_NATIVE_SHA256='d622d11830fb0d946c1b41301ffbe409e213283329013e3ae5a30b447f6f5b78'

def native_sha(batches):
 h=hashlib.sha256(b'JYWM'+struct.pack('<II',1,len(batches)))
 for b in batches:
  for name in ('group','material'):
   encoded=b[name].encode();h.update(struct.pack('<I',len(encoded)));h.update(encoded)
  h.update(struct.pack('<II',len(b['vertices']),b['faces'].size));h.update(peer.raw_attributes(b))
 return h.hexdigest()

def restored_prior_fixture(batches,manifest):
 root=Path(__file__).resolve().parent;raw=(root/'testdata'/INVERSE_NAME).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INVERSE_SHA256:raise ValueError('Frozen optimization inverse fixture changed')
 oracle=contract.load_oracle();lookup={(r['before']['group'],r['before']['material']):(i,r) for i,r in enumerate(oracle['changes'])};out=[]
 with np.load(io.BytesIO(raw),allow_pickle=False) as archived:
  for b in batches:
   item=lookup.get((b['group'],b['material']))
   if item is None:out.append(b);continue
   i,pin=item;actual=peer.summarize(b)
   if actual==pin['before']:out.append(b);continue
   if actual!=pin['after']:raise ValueError('Cannot restore unapproved optimization payload')
   result=dict(b);prefix=str(i)+'_'
   if pin['kind']=='static-planar-sea':
    for attr in ('vertices','uv','colors','faces'):result[attr]=archived[prefix+attr].copy()
   else:
    removed=archived[prefix+'removed'];n=pin['before']['vertices'];mask=np.ones(n,bool);mask[removed]=False;keep=np.flatnonzero(mask)
    for attr in ('vertices','uv','colors'):
     result[attr]=np.empty((n,b[attr].shape[1]),dtype=b[attr].dtype);result[attr][keep]=b[attr];result[attr][removed]=archived[prefix+attr]
    result['faces']=keep[b['faces']].astype('<u4')
   if peer.summarize(result)!=pin['before']:raise ValueError('Inverse fixture reconstruction does not match frozen before payload')
   out.append(result)
 if native_sha(out)!=ORIGINAL_NATIVE_SHA256:raise ValueError('Complete inverse fixture is not exact frozen v2.14 native')
 m=copy.deepcopy(manifest)
 for flag in contract.FEATURES:m['features'].pop(flag,None)
 m.pop('meshOptimization',None);m['visualTriangles']=sum(len(b['faces']) for b in out);m['visualMeshCount']=len(out)
 return out,m
