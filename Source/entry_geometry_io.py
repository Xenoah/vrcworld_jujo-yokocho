"""Read immutable JYWM v1 source geometry, including official sharded payloads."""
from pathlib import Path
import gzip, struct, io
import numpy as np

def read_geometry(root, kind='Visual'):
    path=Path(root)/'Assets/TreeTopYokocho/Data'/f'{kind}Meshes.bytes'
    if Path(str(path)+'.gz').exists(): data=gzip.decompress(Path(str(path)+'.gz').read_bytes())
    elif (parts:=sorted(path.parent.glob(path.name+'.gz.part[0-9][0-9][0-9]'))): data=gzip.decompress(b''.join(p.read_bytes() for p in parts))
    else: data=path.read_bytes()
    return parse_geometry(data)

def parse_geometry(data):
    f=io.BytesIO(data)
    assert f.read(4)==b'JYWM'
    version,count=struct.unpack('<II',f.read(8));assert version==1
    out=[]
    for _ in range(count):
        names=[f.read(struct.unpack('<I',f.read(4))[0]).decode() for _ in range(2)]
        nv,ni=struct.unpack('<II',f.read(8))
        v=np.frombuffer(f.read(nv*12),'<f4').reshape(-1,3).copy()
        uv=np.frombuffer(f.read(nv*8),'<f4').reshape(-1,2).copy()
        c=np.frombuffer(f.read(nv*4),'u1').reshape(-1,4).copy()
        ix=np.frombuffer(f.read(ni*4),'<u4').reshape(-1,3).copy()
        out.append(dict(group=names[0],material=names[1],vertices=v,uv=uv,colors=c,faces=ix))
    assert f.read()==b''
    return out

if __name__=='__main__':
    import sys
    for kind in ['Visual','Collision']:
        for m in read_geometry(sys.argv[1],kind):
            v=m['vertices'];tri=v[m['faces']]
            keep=np.all(tri.max(axis=1)>[-12,-36,134.1],axis=1)&np.all(tri.min(axis=1)<[12,-22,137],axis=1)
            if np.any(keep):
                p=tri[keep].reshape(-1,3)
                print(kind,m['group'],m['material'],len(p)//3,p.min(axis=0).round(3),p.max(axis=0).round(3))
