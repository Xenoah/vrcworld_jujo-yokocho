#!/usr/bin/env python3
"""Decode final PNGs and independently verify map contracts and seam bounds."""
from pathlib import Path
import json,hashlib,sys,importlib.util
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('synth',ROOT/'Source/author_seamless_pbr.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
origin_bytes=(ROOT/'Docs/authored_pbr_origin.json').read_bytes()
origin=json.loads(origin_bytes)
origin_sha256=hashlib.sha256(origin_bytes).hexdigest()
results=[];fail=[]

def check(name,passed,detail):
 r={'test':name,'pass':bool(passed),'detail':detail};results.append(r)
 if not passed:fail.append(name)

check('no_external_inputs',origin['externalInputs']==[] and origin['downloads']==[] and origin['imageModelUsed'] is False,'Generator reads no source photographs, scans, downloaded textures or model-generated images.')
check('source_hash_matches',hashlib.sha256((ROOT/'Source/author_seamless_pbr.py').read_bytes()).hexdigest()==origin['sourceSha256'],origin['sourceSha256'])
# The primitives remain continuous at u+1/v+1; final encoded edges need not
# match because border pixels are sampled one pixel apart, not duplicated.
rng=np.random.default_rng(9821);x=rng.uniform(-2,2,(89,71));y=rng.uniform(-2,2,(89,71))
a=s.noise(93821,79,13,x=x,y=y);du=s.noise(93821,79,13,x=x+1,y=y);dv=s.noise(93821,79,13,x=x,y=y+1)
err=max(float(np.abs(a-du).max()),float(np.abs(a-dv).max()))
check('periodic_noise_identity',err<2e-5,{'maximumFloatDifference':err,'threshold':2e-5})
# Analytic orientation: positive dH/dU tilts tangent normal toward -X;
# positive derivative down image rows tilts OpenGL normal toward +Y.
yy,xx=np.mgrid[:64,:64]/64
h=np.sin(xx*2*np.pi)+np.sin(yy*2*np.pi)
n=s.normal_from_height(h,{'heightRangeMeters':.01,'physicalTileMeters':[1,1]})
check('normalGL_orientation',n[0,0,0]<0 and n[0,0,1]>0 and n[0,0,2]>0,{'normalAtPositiveXYImageDerivative':n[0,0].tolist()})
for fam in origin['families']:
 arrays={}
 for channel,meta in fam['maps'].items():
  path=ROOT/meta['path'];im=Image.open(path);im.load();raw=np.asarray(im)
  a=raw.astype(np.float32)/(65535 if channel=='height' else 255);arrays[channel]=a
  check(f"{fam['family']}/{channel}/sha",hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256'],meta['sha256'])
  expected=(2048,2048) if channel=='albedo' else (1024,1024)
  check(f"{fam['family']}/{channel}/resolution",im.size==expected,{'actual':im.size,'expected':expected})
  check(f"{fam['family']}/{channel}/finite_bounds",np.isfinite(a).all() and a.min()>=0 and a.max()<=1,{'min':float(a.min()),'max':float(a.max())})
  seams=s.seam_stats(a)
  check(f"{fam['family']}/{channel}/wrap_steps",all(v['ratio']<1.8 for v in seams.values()),{'rationale':'A wrap step is one ordinary sample interval, not an edge-copy match. It must stay below 1.8x interior mean for both axes.','measures':seams})
  if channel=='height':check(f"{fam['family']}/height/16bit",raw.dtype==np.uint16 or (raw.dtype==np.int32 and raw.max()>255),{'dtype':str(raw.dtype),'maximum':int(raw.max())})
 arm=arrays['arm'];check(f"{fam['family']}/nonmetallic",np.all(arm[:,:,2]==0),'ARM blue channel must be exactly zero.')
 check(f"{fam['family']}/roughness_bounds",arm[:,:,1].min()>=.35 and arm[:,:,1].max()<=.97,{'min':float(arm[:,:,1].min()),'max':float(arm[:,:,1].max())})
 normal=arrays['normalGL']*2-1;length=np.linalg.norm(normal,axis=-1)
 check(f"{fam['family']}/quantized_unit_normal",np.max(np.abs(length-1))<.007,{'maximumLengthError':float(np.max(np.abs(length-1)))})
 check(f"{fam['family']}/positive_normalZ",normal[:,:,2].min()>.25,{'minimumZ':float(normal[:,:,2].min())})
 expected=s.normal_from_height(arrays['height'],fam)
 dot=np.sum(expected*normal/length[...,None],axis=-1)
 angle=np.degrees(np.arccos(np.clip(dot,-1,1)))
 check(f"{fam['family']}/normal_height_coherence",np.percentile(angle,99.9)<.5,{'angularErrorP99_9Degrees':float(np.percentile(angle,99.9)),'maximumDegrees':float(angle.max())})
report={'schema':1,'originSha256':origin_sha256,'scope':'Numerical and encoded map validation only; not aesthetic acceptance or Unity runtime validation','passed':not fail,'count':len(results),'failed':fail,'checks':results}
(ROOT/'Docs/authored_pbr_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':not fail,'count':len(results),'failed':fail},indent=2));sys.exit(bool(fail))
