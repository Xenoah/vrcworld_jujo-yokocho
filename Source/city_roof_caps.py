"""Remove only 834 strictly enclosed city bracket top caps; visual geometry only."""
import numpy as np
KEY=('Landscape/DetailCityRoofs','DarkTimber')
FEATURE='city_roof_hidden_caps'

def selection(vertices,faces):
    v=np.asarray(vertices,dtype='<f4').astype(float);f=np.asarray(faces)
    if v.shape!=(30024,3) or f.shape!=(15012,3):raise ValueError('Unexpected city roof topology')
    expected=np.array([[4*j+a for a in t] for j in range(6) for t in ((0,1,2),(0,2,3))])
    if not np.array_equal(f.reshape(-1,12,3)-np.arange(1251)[:,None,None]*24,np.broadcast_to(expected,(1251,12,3))):raise ValueError('City box topology changed')
    remove=[];minimum=float('inf')
    for house in range(139):
        for side in range(2):
            i=house*9+side;tri=v[f[i*12:(i+1)*12]];center=v[i*24:(i+1)*24].mean(0)
            n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);n/=np.linalg.norm(n,axis=1)[:,None]
            if not np.all(np.sum(n*(tri[:,0]-center),axis=1)>0):raise ValueError('Fascia winding is not outward')
            _,idx=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True);ff=idx.reshape(-1,3)
            edges=np.sort(np.concatenate((ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]])),axis=1)
            if not np.all(np.unique(edges,axis=0,return_counts=True)[1]==2):raise ValueError('Fascia shell is not closed')
            # Every fascia vertex must lie within all actual outward planes.
            if np.max(np.einsum('cfi,fi->cf',v[i*24:(i+1)*24,None,:]-tri[None,:,0,:],n))>1e-7:raise ValueError('Fascia is not convex')
            for j in range(3):
                k=house*9+3+side*3+j;cap=v[k*24+4:k*24+8]
                clear=-float(np.max(np.einsum('cfi,fi->cf',cap[:,None,:]-tri[None,:,0,:],n)))
                if clear<.05:raise ValueError('Bracket cap lacks enclosure clearance')
                minimum=min(minimum,clear);remove.extend((k*12+2,k*12+3))
    face_keep=np.ones(len(f),bool);face_keep[remove]=False;keep=np.unique(f[face_keep]);remap=np.full(len(v),-1,dtype=np.int64);remap[keep]=np.arange(len(keep))
    if len(keep)!=26688 or face_keep.sum()!=13344:raise ValueError('Unexpected cap reduction')
    if not np.array_equal(v.min(0),v[keep].min(0)) or not np.array_equal(v.max(0),v[keep].max(0)):raise ValueError('City bounds changed')
    return keep,face_keep,remap[f[face_keep]].astype('<u4'),minimum

def optimize(geometry):
    from peer_culling_contract import summarize
    from city_roof_caps_contract import load_oracle
    b=geometry.batches[KEY];pin=load_oracle();native=dict(group=KEY[0],material=KEY[1],vertices=b['v'],faces=b['f'],uv=b['uv'],colors=(b['colors']*255).astype('u1'))
    if geometry.materials.get(KEY[1])!=pin['material']:raise ValueError('City opaque material descriptor differs from reviewed original')
    if summarize(native)!=pin['before']:raise ValueError('City source payload differs from reviewed original')
    keep,mask,faces,clear=selection(b['v'],b['f']);b['f']=faces
    for attr in ('v','uv','colors'):b[attr]=np.asarray(b[attr])[keep].copy()
    b.pop('authored_tints',None)
    native.update(vertices=b['v'],faces=b['f'],uv=b['uv'],colors=(b['colors']*255).astype('u1'))
    if summarize(native)!=pin['after']:raise ValueError('City optimized payload differs from reviewed result')
    return dict(version=1,removedTriangles=1668,removedVertices=3336,savedNativeBytes=100080,minimumEnclosureClearanceMetres=clear)
