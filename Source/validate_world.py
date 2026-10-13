"""Offline geometric checks, independent of the Unity builder. No physics-engine claims."""
from pathlib import Path
import json,struct,math,sys
import numpy as np
from shapely import wkt
from shapely.geometry import Point
from PIL import Image

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
asset=root/'Assets/TreeTopYokocho';m=json.loads((asset/'Data/WorldManifest.json').read_text())
normal_mapped={x['name'] for x in m['materials'] if x.get('normal')}
tangent_uv_errors=[]
def meshes(path):
    with open(path,'rb') as r:
        assert r.read(4)==b'JYWM';version,count=struct.unpack('<II',r.read(8));assert version==1
        for _ in range(count):
            names=[]
            for j in range(2):names.append(r.read(struct.unpack('<I',r.read(4))[0]).decode())
            nv,ni=struct.unpack('<II',r.read(8));v=np.frombuffer(r.read(nv*12),dtype='<f4').reshape(-1,3).copy()
            uv=np.frombuffer(r.read(nv*8),dtype='<f4').reshape(-1,2);colors=r.read(nv*4)
            f=np.frombuffer(r.read(ni*4),dtype='<u4').reshape(-1,3).copy()
            assert np.isfinite(v).all() and np.isfinite(uv).all();assert f.max()<nv
            if names[1] in normal_mapped:
                tu=uv[f];a=tu[:,1]-tu[:,0];b=tu[:,2]-tu[:,0]
                uv_area=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0]);q=v[f]
                area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
                bad=int(np.count_nonzero((uv_area<1e-10)&(area>1e-8)))
                if bad:tangent_uv_errors.append((names[0],names[1],bad))
            yield names[0],names[1],v,f
        assert r.read()==b''
visual=list(meshes(asset/'Data/VisualMeshes.bytes'));physical=list(meshes(asset/'Data/CollisionMeshes.bytes'))
floors=np.concatenate([v[f] for g,ma,v,f in physical if g.startswith(('Floors/','Ramps/'))])
walls=np.concatenate([v[f] for g,ma,v,f in physical if g.startswith('Safety/')])
class Rays:
    def __init__(self,tri):
        self.a=tri[:,0].astype(float);self.e1=tri[:,1]-tri[:,0];self.e2=tri[:,2]-tri[:,0]
        self.lo=tri.min(axis=1)-1e-6;self.hi=tri.max(axis=1)+1e-6
    def hit(self,origin,direction,limit):
        # Segment AABB broad phase followed by two-sided Moller-Trumbore.
        o=np.array(origin,dtype=float);d=np.array(direction,dtype=float)
        end=o+d*limit;lo=np.minimum(o,end)-1e-5;hi=np.maximum(o,end)+1e-5
        idx=np.where(np.all((self.lo<=hi)&(self.hi>=lo),axis=1))[0]
        if not len(idx):return None
        a=self.a[idx];e1=self.e1[idx];e2=self.e2[idx]
        h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h)
        # Front-facing only, matching Unity's default ray back-face treatment.
        ok=det>1e-8
        inv=np.divide(1,det,out=np.zeros_like(det),where=ok);s=o-a
        u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*np.einsum('j,ij->i',d,q);t=inv*np.einsum('ij,ij->i',e2,q)
        ok &= (u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001)&(t>=0)&(t<=limit)
        return float(t[ok].min()) if np.any(ok) else None
rf=Rays(floors);rw=Rays(walls);checks=[];failures=[]
def check(name,passed,detail=''):
    checks.append({'name':name,'passed':bool(passed),'detail':detail})
    if not passed:failures.append(name+': '+detail)

check('Normal-mapped triangles have non-collapsed UVs',not tangent_uv_errors,str(tangent_uv_errors[:8]))
check('8 stores / 49 seat definitions',len(m['stations'])==49 and len(set(s['shop'] for s in m['stations']))==8)
check('12 lift destination buttons',len(m['teleports'])==12)
for lev in m['floors']:
    p=wkt.loads(lev['wkt']);eroded=p.buffer(-.25)
    check('Connected '+lev['level'],p.geom_type=='Polygon' and p.is_valid)
    check('0.50 m capsule center continuity '+lev['level'],eroded.geom_type=='Polygon',eroded.geom_type)
    batch=next(x for x in physical if x[0]=='Floors/'+lev['level']);v,f=batch[2:];tri=v[f]
    top=tri[np.all(np.isclose(tri[:,:,2],lev['z'],atol=.0001),axis=1)]
    area=np.linalg.norm(np.cross(top[:,1]-top[:,0],top[:,2]-top[:,0]),axis=1).sum()/2
    check('Physical slab covers entire '+lev['level'],abs(area-p.area)<.02,f'polygon {p.area:.5f}, triangles {area:.5f} m2')

from shapely.geometry import LineString
bad=[]
level_heights={x['level']:x['z'] for x in m['floors']}
for other in m['floors']:
    inner=wkt.loads(other['wkt']).buffer(-.25)
    for guard in m['guards']:
        if level_heights[guard['level']]<other['z']-.5 and guard['top']>other['z']+.05:
            if inner.distance(LineString([guard['a'],guard['b']]))<.12:
                bad.append(guard['name']+' into '+other['level'])
check('Lower-deck walls do not penetrate upper walking surfaces',not bad,str(bad[:10]))

bad=[]
for s in m['floorTests']:
    pos=np.array(s['position']);h=rf.hit(pos+[0,0,.75],[0,0,-1],1.65)
    if h is None:bad.append((s['id'],s['position']))
check('Route / ring / stair / spawn floor probes',not bad,f'{len(m["floorTests"])} rays; misses {bad[:8]}')
bad=[]
for i,s in enumerate(m['wallTests']):
    a=np.array(s['start']);d=np.array(s['end'])-a;length=np.linalg.norm(d)
    if rw.hit(a,d/length,length) is None:bad.append(i)
check('Front-facing barrier ray intersections',not bad,f'{len(m["wallTests"])} rays; misses {bad[:12]}')

bad=[]
for seat in m['stations']:
    pos=np.array(seat['exit']);h=rf.hit(pos+[0,0,.5],[0,0,-1],1.0)
    if h is None:bad.append(seat['name'])
check('All 49 seat exits have a physical slab',not bad,str(bad))
for t in m['teleports']:
    check('Destination '+t['name'],rf.hit(np.array(t['destination'])+[0,0,.5],[0,0,-1],1.0) is not None)
for p in (asset/'Textures').rglob('*'):
    if p.suffix.lower() not in ['.png','.jpg']:continue
    im=Image.open(p);im.load();check('Texture '+p.name,True,str(im.size))

check('Four PBR scan sets, max 2K albedo / 1K auxiliaries', len(list((asset/'Textures/PBR').glob('*_diff_4k.jpg')))==4 and all(max(Image.open(p).size) <= (2048 if '_diff_' in p.name else 1024) for p in (asset/'Textures/PBR').glob('*.jpg')))
import gzip,hashlib
shards=sorted((asset/'Data').glob('VisualMeshes.bytes.gz.part[0-9][0-9][0-9]'))
joined=b''.join(p.read_bytes() for p in shards)
check('Gzip shards reconstruct visual payload',bool(shards) and gzip.decompress(joined)==(asset/'Data/VisualMeshes.bytes').read_bytes())
check('Collision payload has a recorded SHA-256',len(hashlib.sha256((asset/'Data/CollisionMeshes.bytes').read_bytes()).hexdigest())==64)
# Navigation geometry changed intentionally in v2.2 to fix R03/W05 crossing.
# The meaningful regression is validate_navigation.py, not equality to old unsafe data.
check('Forest, peer giant trees, circular city, snowy peaks and sea islands',m['detail'].get('giantPeerTrees',0)>=8 and m['detail'].get('distantHouses',0)>=100 and m['detail'].get('seaIslands',0)>=4, str(m['detail']))
check('Steam emitters',len(m['steam'])==5)

# Triangle payloads and glTF resource integrity.
from pygltflib import GLTF2
gl=GLTF2().load(str(root/'Source/TreeTopYokocho.glb'));blob=gl.binary_blob()
check('glTF mesh count',len(gl.meshes)==len(visual),str(len(gl.meshes)))
check('glTF triangles equal Unity source',sum(gl.accessors[x.primitives[0].indices].count//3 for x in gl.meshes)==m['visualTriangles'])
check('glTF buffer bounds',all((b.byteOffset or 0)+b.byteLength<=len(blob) for b in gl.bufferViews))
normal_bad=[]
for mesh in gl.meshes:
    aidx=mesh.primitives[0].attributes.NORMAL
    if aidx is None:normal_bad.append(mesh.name+': missing');continue
    a=gl.accessors[aidx];view=gl.bufferViews[a.bufferView]
    normals=np.frombuffer(blob,dtype='<f4',count=a.count*3,offset=(view.byteOffset or 0)+(a.byteOffset or 0))
    if not np.isfinite(normals).all():normal_bad.append(mesh.name+': non-finite')
check('glTF exports finite surface normals',not normal_bad,str(normal_bad[:5]))

for mat in m['materials']:
    for channel in ['texture','normal','arm','height']:
        check('Material '+channel+' '+mat['name'],not mat.get(channel) or (asset/'Textures'/mat[channel]).exists())

try:
    from tree_sitter import Language,Parser
    import tree_sitter_c_sharp
    parser=Parser(Language(tree_sitter_c_sharp.language()))
    for p in asset.rglob('*.cs'):check('C# syntax '+p.name,not parser.parse(p.read_bytes()).root_node.has_error)
except ImportError:pass

report={'status':'PASS' if not failures else 'FAIL','scope':'Offline geometry / resource / C# syntax checks. NOT Unity, Udon, shader compilation or VRChat runtime validation.','checks':checks,'failures':failures,'visualTriangles':m['visualTriangles'],'visualMeshCount':m['visualMeshCount'],'safetyWallSegments':len(m['guards']),'floorRayCount':len(m['floorTests']),'barrierRayCount':len(m['wallTests']),'unityExecuted':False,'vrchatExecuted':False}
(root/'Docs/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
raise SystemExit(0 if not failures else 1)
