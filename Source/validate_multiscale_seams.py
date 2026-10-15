"""Read-only multi-scale border diagnostics. Not a visual art admission."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];origin=json.loads((ROOT/'Docs/authored_pbr_origin.json').read_text());out=[];fail=[]
for fam in origin['families']:
 for channel in ('albedo','normalGL','arm','height'):
  path=ROOT/fam['maps'][channel]['path'];a=np.array(Image.open(path)).astype(np.float32)/(65535 if channel=='height' else 255)
  if a.ndim==2:a=a[...,None]
  for reduction in (1,2,4,8,16):
   n=len(a)//reduction;b=a.reshape(n,reduction,n,reduction,a.shape[-1]).mean((1,3))
   axes={}
   for axis,label in ((1,'U'),(0,'V')):
    delta=np.abs(np.diff(b,axis=axis));wrap=np.abs(np.take(b,0,axis)-np.take(b,-1,axis));ratio=float(wrap.mean()/max(float(delta.mean()),1e-12))
    # Also test boundary curvature (gradient transitions), so an abrupt change
    # in derivative cannot hide behind low raw edge difference.
    curv=np.abs(np.roll(b,-1,axis)-2*b+np.roll(b,1,axis));edgecurv=(np.take(curv,0,axis)+np.take(curv,-1,axis))/2
    curvature_ratio=float(edgecurv.mean()/max(float(curv.mean()),1e-12))
    axes[label]={'wrapStepRatio':ratio,'boundaryCurvatureRatio':curvature_ratio,'interiorStepMean':float(delta.mean()),'wrapStepMean':float(wrap.mean())}
    if ratio>2 or curvature_ratio>2:fail.append([fam['family'],channel,reduction,label,ratio,curvature_ratio])
   out.append({'family':fam['family'],'channel':channel,'areaReduction':reduction,'axes':axes})
r={'schema':1,'scope':'Read-only multi-scale periodic edge and boundary-derivative diagnostics; not art acceptance.','status':'PASS' if not fail else 'FAIL','originSha256':hashlib.sha256((ROOT/'Docs/authored_pbr_origin.json').read_bytes()).hexdigest(),'failed':fail,'checks':out}
(ROOT/'Docs/multiscale_seam_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'checks':len(out),'failed':fail},indent=2))
