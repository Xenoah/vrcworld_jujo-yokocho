"""Each physical suspension link must contact its emblem and supporting arm."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Source'))
from test_venue_projecting_signs import make
def intersect(a,bs):
    ea=np.roll(a,-1,axis=0)-a;eb=np.roll(bs,-1,axis=1)-bs
    na=np.cross(ea[0],ea[1]);nb=np.cross(eb[:,0],eb[:,1])
    axes=[np.broadcast_to(na,(len(bs),3)),nb]
    for aa in ea:
        for bb in range(3):axes.append(np.cross(aa,eb[:,bb]))
        axes.append(np.broadcast_to(np.cross(na,aa),(len(bs),3)))
    for bb in range(3):axes.append(np.cross(nb,eb[:,bb]))
    valid=np.ones(len(bs),bool)
    for axis in axes:
        length=np.linalg.norm(axis,axis=1);active=length>1e-12
        ax=axis/np.where(active,length,1)[:,None]
        pa=np.einsum('vd,nd->nv',a,ax);pb=np.einsum('nvd,nd->nv',bs,ax)
        separate=(pa.max(1)<pb.min(1)-1e-8)|(pb.max(1)<pa.min(1)-1e-8)
        valid &= ~(active&separate)
        if not valid.any():break
    return valid
def contacts(a,b):
 lo=b.min(1);hi=b.max(1)
 for tri in a:
  near=((hi>=tri.min(0)-1e-8)&(lo<=tri.max(0)+1e-8)).all(1)
  if near.any() and intersect(tri,b[near]).any():return True
 return False
rows=[]
for idx in range(8):
 g,m,*_=make(idx);components=m['parts'][0]['components']
 def triangles(component):
  out=[]
  for r in component['ranges']:
   b=g.batches[tuple(r['key'])];ff=np.array(b['f'])[r['triangleStart']:r['triangleStart']+r['triangleCount']]
   out.append(np.array(b['v'])[ff])
  return np.concatenate(out)
 body=triangles(next(c for c in components if c['role']=='dimensional_emblem'))
 bracket=triangles(next(c for c in components if c['role']=='structural_support'))
 suspension=triangles(next(c for c in components if c['role']=='suspension_hardware'))
 assert len(suspension)%128==0
 links=[]
 for first in range(0,len(suspension),128):
  link=suspension[first:first+128]
  links.append(dict(index=first//128+1,contactsBody=bool(contacts(link,body)),contactsBracket=bool(contacts(link,bracket))))
 rows.append(dict(shop=m['shop'],links=links));print(m['shop'],links,flush=True)
out=dict(sourceSha256=hashlib.sha256((ROOT/'Source/venue_projecting_signs.py').read_bytes()).hexdigest(),rows=rows,status='PASS' if all(x['contactsBody'] and x['contactsBracket'] for r in rows for x in r['links']) else 'FAIL')
(ROOT/'Docs/suspension-contact-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])

raise SystemExit(out['status'] != 'PASS')
