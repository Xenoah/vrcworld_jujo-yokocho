"""Independent cap-relocation and twelve-box proof; not an art approval."""
from collections import Counter,defaultdict
import io
from pathlib import Path
import numpy as np
import s05_pendant_contract as c
INVERSE_NAME='s05_pendant_inverse_2_18.npz'
INVERSE_SHA256='872a4d1b32cae3164bd56ce3c97a719dd6fa2bc38269a5f515bcacb48577e7c7'

def old_pale():
    raw=(Path(__file__).resolve().parent/'testdata'/INVERSE_NAME).read_bytes()
    if c.sha(raw)!=INVERSE_SHA256:raise ValueError('Immutable S05 pale-joinery evidence changed')
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        return dict(group=c.OLD_KEY[0],material=c.OLD_KEY[1],**{k:archive[k].copy() for k in ('vertices','uv','colors','faces')})
def local_points(vertices,manifest):
    shop=next(s for s in manifest['shopPersonality']['shops'] if s['id']=='S05');f=shop['frame']
    axes=np.asarray([f['right'],f['front'],f['up']],float)
    return (np.asarray(vertices,float)-np.asarray(f['origin']))@axes.T

def audit(batches,manifest):
    from peer_culling_contract import triangle_records
    lookup={c.key(b):b for b in batches};old=old_pale();pale=lookup[c.OLD_KEY];dark=lookup[c.NEW_KEY];errors=[]
    def check(value,reason):
        if not value:errors.append(dict(reason=reason))
    def records(batch):return [r.tobytes() for r in triangle_records(batch)]
    ov=local_points(old['vertices'],manifest);tri=ov[old['faces']];masks=[]
    # Float tolerance is used only to select the immutable caps from known
    # float32 positions. Their entire position/UV/Color32/winding payload must
    # then move with exact byte equality, not tolerance.
    for x in (-1.77,1.77):
        for z in (2.24,2.45):
            center=np.array([x,.4,z]);extent=np.array([.75,.51,.025])/2
            mask=np.all(np.abs(tri-center)<=extent+2e-5,axis=(1,2))
            check(int(mask.sum())==44,'Each of four old caps must contain exactly44 immutable chamfer triangles');masks.append(mask)
    selected=np.any(masks,axis=0);check(int(selected.sum())==176,'Four immutable caps must not overlap')
    cap=dict(old,faces=old['faces'][selected]);retained=dict(old,faces=old['faces'][~selected])
    check(Counter(records(pale))==Counter(records(retained)),'Pale sign/frame remainder geometry/UV/color/winding changed')
    cap_records=Counter(records(cap));dark_records=records(dark)
    check(not(cap_records-Counter(dark_records)),'Four cap payloads were not preserved exactly when moved to DarkTimber')
    remaining=[];needed=cap_records.copy()
    for i,record in enumerate(dark_records):
        if needed[record]:needed[record]-=1
        else:remaining.append(i)
    check(len(remaining)==144,'Exactly144 newly added stile triangles required')
    vertices=local_points(dark['vertices'],manifest);triangles=vertices[dark['faces'][remaining]];specs=[]
    for x in (-1.77,1.77):
        for sx in (-1,1):
            for sy in (-1,1):specs.append((np.array([x+sx*.361,.4+sy*.244,2.345]),np.array([.028,.020,.210])))
        for sy in (-1,1):specs.append((np.array([x,.4+sy*.244,2.345]),np.array([.0175,.020,.210])))
    assigned=np.zeros(len(triangles),int)
    for number,(center,size) in enumerate(specs):
        extent=size/2;selected=np.all(np.abs(triangles-center)<=extent+2e-5,axis=(1,2));assigned+=selected
        ts=triangles[selected];check(len(ts)==12,'Each declared stile must have exactly12 triangles')
        faces=defaultdict(list)
        for t in ts:
            signs=np.where(t>=center,1,-1);corners=center+signs*extent
            check(np.all(np.abs(t-corners)<2e-5),'Stile vertex moved outside exact declared box corners')
            normal=np.cross(t[1]-t[0],t[2]-t[0]);axis=int(np.argmax(np.abs(normal)));direction=int(signs[0,axis])
            check(np.all(signs[:,axis]==direction) and normal[axis]*direction>1e-10,'Stile triangle is not an outward rectangular face')
            faces[(axis,direction)].append([tuple(int(v) for v in p) for p in signs])
        check(set(faces)=={(a,s) for a in range(3) for s in (-1,1)},'Stile must have all six outward faces')
        for (axis,_),pairs in faces.items():
            check(len(pairs)==2,'Stile rectangular face must have two triangles')
            if len(pairs)!=2:continue
            a,b=map(set,pairs);shared=a&b;free=[i for i in range(3) if i!=axis]
            check(len(a)==len(b)==3 and len(a|b)==4 and len(shared)==2,'Stile face does not cover four distinct corners')
            if len(shared)==2:
                x,y=list(shared);check(all(x[i]!=y[i] for i in free),'Stile triangles must meet along a diagonal, not overlap')
    check(np.all(assigned==1),'Every new triangle must belong to exactly one of the twelve declared stiles')
    for batch in (pale,dark):
        check(len(np.unique(batch['faces']))==len(batch['vertices']),'Affected native batch acquired unused/hidden vertices')
    union=np.concatenate([pale['vertices'],dark['vertices']])
    check(np.array_equal(union.min(0),old['vertices'].min(0)) and np.array_equal(union.max(0),old['vertices'].max(0)),'Affected union envelope changed')
    return dict(status='FAIL' if errors else 'PASS',errors=errors,exactMovedCapTriangles=176,newStileTriangles=144,stileCount=12,geometryToleranceOnlyForIndependentBoxClassification=2e-5,scope='Old cap and pale-frame triangle attributes/winding exact; twelve closed outward boxes at literal locations; actual after admission remains byte-pinned, not tolerance-based.')
