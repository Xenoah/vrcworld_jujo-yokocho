"""Actual triangle-vs-triangle intersections: new emblem/cloth vs old venue.

Only dedicated structural_support/suspension_hardware ranges and the metal
supports of GuildPennant are excluded. Nothing is removed from route tests.
This is a mechanical authoring diagnostic, not a physics/runtime certificate.
"""
from pathlib import Path
import copy,json,sys,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Source'))
from world_geometry import Geometry
from shop_personality import default_seats
from venue_projecting_signs import add_signs,FOOTPRINTS
import food_venues,nightlife_venues
BASE=Path(sys.argv[1]);manifest=json.loads((BASE/'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
M=dict(wood='Cedar',dark='DarkTimber',counter='Counter',trim='Bronze',wall='Plaster',tile='Kawara',window='WarmWindow',iron='Iron',ceramic='Ceramic',food='Food',red='RedLantern',city='TownLights',menu='MenuAtlas',tea='Tea',soy='Soy',noodle='Noodles',sweet='MatchaSweets')
for module in (food_venues,nightlife_venues):
 for spec in module.material_specs():M[spec['key']]=spec['name']

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
rows=[]
for idx in range(8):
 w,dep=FOOTPRINTS[idx];g=Geometry();g.materials={m['name']:copy.deepcopy(m) for m in manifest['materials']};g.group=f'Shops/S{idx+1:02d}'
 P=lambda x,y,z:np.array([x,y,z],float)
 B=lambda x,y,z,w,d,h,mat:g.box(P(x,y,z),(w,d,h),mat)
 module=food_venues if idx in food_venues.SHOP_IDS else nightlife_venues
 options=dict(seat_specs=default_seats(idx,w,dep),rpg_identity=True)
 if idx==4:options['pendant_refinement']=True
 module.build_venue(g,P,B,w,dep,idx,M,**options)
 old={k:np.array(b['v'])[np.array(b['f'])] for k,b in g.batches.items()}
 report=add_signs(g,P,idx,M,w,dep);hits=[];checked=0
 for comp in report['parts'][0]['components']:
  if comp['role'] not in ('dimensional_emblem','static_cloth_pennant'):continue
  for r in comp['ranges']:
   if comp['role']=='static_cloth_pennant' and r['key'][1] in ('Iron','Bronze'):continue
   batch=g.batches[tuple(r['key'])];fs=np.array(batch['f'])[r['triangleStart']:r['triangleStart']+r['triangleCount']];new=np.array(batch['v'])[fs]
   lo=new.min((0,1));hi=new.max((0,1));checked+=len(new)
   for key,triangles in old.items():
    olo=triangles.min(1);ohi=triangles.max(1)
    ids=np.flatnonzero(((ohi>=lo-1e-8)&(olo<=hi+1e-8)).all(1))
    if not len(ids):continue
    sub=triangles[ids];sl=olo[ids];sh=ohi[ids];matched=[]
    for ni,a in enumerate(new):
     near=((sh>=a.min(0)-1e-8)&(sl<=a.max(0)+1e-8)).all(1)
     if not near.any():continue
     found=np.flatnonzero(near)[intersect(a,sub[near])]
     if len(found):matched.append([int(ni),*[int(ids[k]) for k in found]])
    if matched:hits.append(dict(component=comp['semantic'],newMaterial=r['key'][1],oldKey=list(key),trianglePairs=matched))
 rows.append(dict(shop=report['shop'],checkedNewBodyTriangles=checked,intersectionPairCount=sum(sum(len(x)-1 for x in h['trianglePairs']) for h in hits),hits=hits))
 print(report['shop'],rows[-1]['intersectionPairCount'],'pairs',flush=True)
out=dict(sourceSha256=hashlib.sha256((ROOT/'Source/venue_projecting_signs.py').read_bytes()).hexdigest(),scope='All old venue visual triangles versus every new dimensional-emblem/cloth triangle, except explicitly identified support hardware; source-local exact SAT with 1e-8 m tolerance',rows=rows,status='PASS' if not any(r['intersectionPairCount'] for r in rows) else 'FAIL')
(ROOT/'Docs/body-intersection-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])

raise SystemExit(out['status'] != 'PASS')
