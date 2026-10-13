"""Deterministic, meter-scaled mesh authoring. Source coordinates: X east, Y north, Z up."""
import numpy as np, math, struct, json
from collections import defaultdict
from pathlib import Path
from PIL import Image
import trimesh

class Geometry:
    def __init__(self):
        self.batches={}; self.materials={}; self.group='World'
    def material(self,name,color,texture=None,emission=0,roughness=.8,**pbr):
        self.materials[name]={'name':name,'color':list(color),'texture':texture or '', 'emission':emission,'roughness':roughness,**pbr}
        return name
    def add(self,vertices,faces,mat,uv=None):
        key=(self.group,mat)
        b=self.batches.setdefault(key,{'v':[],'f':[],'uv':[]})
        v=np.asarray(vertices,dtype=float).reshape((-1,3)); f=np.asarray(faces,dtype=np.int32).reshape((-1,3))
        n=len(b['v']); b['v'].extend(v.tolist()); b['f'].extend((f+n).tolist())
        b['uv'].extend(np.asarray(uv if uv is not None else np.zeros((len(v),2))).tolist())
    def box(self,c,s,mat,axes=None):
        c=np.array(c); s=np.array(s)/2
        a=np.eye(3) if axes is None else np.asarray(axes).T
        ps=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])*s
        ps=ps@a.T+c
        v=[];f=[];uv=[]
        for q in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            k=len(v); v.extend(ps[list(q)]); f.extend([[k,k+1,k+2],[k,k+2,k+3]])
            u=np.linalg.norm(ps[q[1]]-ps[q[0]]); w=np.linalg.norm(ps[q[3]]-ps[q[0]])
            uv.extend([(0,0),(u,0),(u,w),(0,w)])
        if np.linalg.det(a)<0:f=np.asarray(f)[:,::-1]
        self.add(v,f,mat,uv)
    def beam(self,a,b,width,mat,depth=None):
        a=np.array(a);b=np.array(b);d=b-a;l=np.linalg.norm(d)
        if l<1e-7:return
        z=d/l; ref=np.array([0,0,1]) if abs(z[2])<.95 else np.array([1,0,0])
        x=np.cross(ref,z);x/=np.linalg.norm(x);y=np.cross(z,x)
        self.box((a+b)/2,(width,depth or width,l),mat,[x,y,z])
    def tube(self,points,radii,mat,segments=12,rough=0):
        ps=np.array(points,dtype=float);v=[];uv=[];f=[]
        distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(ps,axis=0),axis=1))]
        circumference=math.tau*float(np.median(radii))
        for i,p in enumerate(ps):
            t=ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)];t/=np.linalg.norm(t)
            ref=np.array([0,0,1]) if abs(t[2])<.9 else np.array([1,0,0])
            x=np.cross(t,ref);x/=np.linalg.norm(x);y=np.cross(t,x)
            for j in range(segments+1):
                an=j*2*math.pi/segments
                r=radii[i]*(1+rough*(math.sin(7*an+i*.2)+.45*math.sin(13*an-i*.24)))
                r*=1+rough*.35*math.sin(23*an+i*.53)
                v.append(p+r*(math.cos(an)*x+math.sin(an)*y)); uv.append((j/segments*circumference, distances[i]))
            if i:
                for j in range(segments):
                    k=(i-1)*(segments+1)+j;n=k+segments+1
                    f.extend([(k,k+1,n+1),(k,n+1,n)])
        # End caps, winding follows tube.
        for ring,sgn in [(0,-1),(len(ps)-1,1)]:
            k=len(v);v.append(ps[ring]);uv.append((.5,.5));start=ring*(segments+1)
            for j in range(segments):
                f.append((k,start+j+1,start+j) if sgn<0 else (k,start+j,start+j+1))
        self.add(v,f,mat,uv)
    def cylinder(self,c,r,h,mat,n=12,r2=None):
        c=np.array(c);self.tube([c-[0,0,h/2],c+[0,0,h/2]],[r,r if r2 is None else r2],mat,n)
    def sphere(self,c,s,mat,n=12,rings=7):
        v=[];f=[];uv=[]
        for i in range(rings+1):
            a=math.pi*i/rings
            for j in range(n+1):
                b=2*math.pi*j/n
                noise=1
                if mat.startswith(('Foliage','ForestCanopy')):
                    noise+=math.sin(a)*(.14*math.sin(3*b+2*a+c[0])+.08*math.sin(7*b-3*a+c[1]))
                v.append(np.array(c)+np.array(s)*np.array([math.sin(a)*math.cos(b),math.sin(a)*math.sin(b),math.cos(a)])*noise)
                uv.append((j/n,i/rings))
        for i in range(rings):
            for j in range(n):
                k=i*(n+1)+j
                if i: f.append((k,k+1,k+n+1))
                if i<rings-1:f.append((k+1,k+n+2,k+n+1))
        # Parametrization above is clockwise from outside; reverse.
        self.add(v,np.array(f)[:,::-1],mat,uv)
    def quad(self,v,mat,uv=None,double=False):
        f=[(0,1,2),(0,2,3)]
        uv=uv or [(0,0),(1,0),(1,1),(0,1)]
        if double:
            # Keep opposite sides' normals independent.
            v=list(v)+list(v);uv=list(uv)+list(uv);f.extend([(6,5,4),(7,6,4)])
        self.add(v,f,mat,uv)
    def compact(self):
        for b in self.batches.values():
            b['v']=np.asarray(b['v'],dtype=np.float32);b['f']=np.asarray(b['f'],dtype=np.uint32);b['uv']=np.asarray(b['uv'],dtype=np.float32)
        # Split very large foliage/terrain batches spatially during authoring.
        # Store color variation as a stable object-position tint, not fake light.
    def bake_mood(self,lights):
        for (group,mat),b in self.batches.items():
            v=np.asarray(b['v']);c=np.ones((len(v),3))
            if mat.startswith(('Foliage','ForestCanopy')):
                variation=.79+.18*(.5+.5*np.sin(v[:,0]*.43+v[:,1]*.71+v[:,2]*.28))
                c*=variation[:,None]
            b['colors']=np.column_stack([c,np.ones(len(v))]).astype(np.float32)
    def repair_normal_uvs(self):
        """Give normal-mapped side faces a finite tangent basis.

        Horizontal UV projection collapses on extruded deck sides. Preserve
        valid UVs; split only collapsed faces and project into their own plane.
        """
        repaired=0
        for (group,mat),b in self.batches.items():
            if not self.materials[mat].get('normal'):continue
            f=b['f'];q=b['v'][f];u=b['uv'][f]
            e=u[:,1]-u[:,0];h=u[:,2]-u[:,0]
            uv_area=np.abs(e[:,0]*h[:,1]-e[:,1]*h[:,0])
            area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
            bad=np.where((uv_area<1e-10)&(area>1e-8))[0]
            nv=[];nuv=[];offset=len(b['v'])
            for i in bad:
                p=q[i];right=p[1]-p[0];right/=np.linalg.norm(right)
                normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal)
                up=np.cross(normal,right)
                nv.extend(p);nuv.extend(np.column_stack([p@right,p@up]))
                f[i]=np.arange(offset,offset+3);offset+=3
            if len(bad):
                b['v']=np.concatenate([b['v'],np.array(nv,dtype=np.float32)])
                b['uv']=np.concatenate([b['uv'],np.array(nuv,dtype=np.float32)])
                repaired+=len(bad)
        return repaired
    def save_binary(self,path):
        """Native source coordinates. Unity importer reflects Y/Z and reverses winding."""
        with open(path,'wb') as out:
            out.write(b'JYWM');out.write(struct.pack('<II',1,len(self.batches)))
            for (group,mat),b in self.batches.items():
                for s in [group,mat]:
                    encoded=s.encode();out.write(struct.pack('<I',len(encoded)));out.write(encoded)
                out.write(struct.pack('<II',len(b['v']),len(b['f'])*3))
                out.write(np.asarray(b['v'],dtype='<f4').tobytes());out.write(np.asarray(b['uv'],dtype='<f4').tobytes());out.write((b.get('colors',np.ones((len(b['v']),4)))*255).astype('u1').tobytes());out.write(np.asarray(b['f'],dtype='<u4').tobytes())
    def save_glb(self,path,texture_dir,max_texture=2048):
        scene=trimesh.Scene(); mats={}
        cache={}
        def tex(filename):
            if not filename:return None
            if filename not in cache:
                im=Image.open(Path(texture_dir)/filename);im.load()
                if max(im.size)>max_texture:
                    im.thumbnail((max_texture,max_texture),Image.Resampling.LANCZOS)
                # JPEG keeps the editable glTF compact; alpha images retain PNG.
                im.format='PNG' if im.mode=='RGBA' else 'JPEG';cache[filename]=im
            return cache[filename]
        for name,m in self.materials.items():
            texture=tex(m['texture'])
            mats[name]=trimesh.visual.material.PBRMaterial(name=name,baseColorFactor=[int(min(1,x)*255) for x in m['color']]+[255],baseColorTexture=texture,normalTexture=tex(m.get('normal')),metallicRoughnessTexture=tex(m.get('arm')),occlusionTexture=tex(m.get('arm')),metallicFactor=m.get('metallic',0),roughnessFactor=m['roughness'],emissiveFactor=[min(1,x*m['emission']) for x in m['color']],emissiveTexture=texture if m['emission'] else None,doubleSided=m.get('doubleSided',False) or m.get('shader')=='Foliage' or name=='Kawara',alphaMode=m.get('alphaMode', 'MASK' if m.get('alphaClip') else 'OPAQUE'),alphaCutoff=m.get('alphaClip',.5))
        for (group,mat),b in self.batches.items():
            # glTF is Y-up right-handed: (x,z,-y).
            v=b['v'][:,[0,2,1]].copy();v[:,2]*=-1
            mesh=trimesh.Trimesh(v,b['f'],process=False)
            mesh.visual=trimesh.visual.TextureVisuals(uv=b['uv']*self.materials[mat].get('uvScale',1),material=mats[mat])
            scene.add_geometry(mesh,node_name=group+'__'+mat,geom_name=group+'__'+mat)
        # Trimesh supplies consistent normals and embedded textures; append COLOR_0
        # without sacrificing the texture UV set.
        from pygltflib import GLTF2,BufferView,Accessor
        temp=path.with_suffix('.tmp.glb');temp.write_bytes(scene.export(file_type='glb',include_normals=True))
        gltf=GLTF2().load(str(temp));blob=bytearray(gltf.binary_blob())
        byname={g+'__'+m:b for (g,m),b in self.batches.items()}
        for mesh in gltf.meshes:
            b=byname[mesh.name]
            while len(blob)%4:blob.append(0)
            data=np.asarray(b.get('colors',np.ones((len(b['v']),4))),dtype='<f4').tobytes()
            offset=len(blob);blob.extend(data)
            vi=len(gltf.bufferViews);gltf.bufferViews.append(BufferView(buffer=0,byteOffset=offset,byteLength=len(data),target=34962))
            ai=len(gltf.accessors);gltf.accessors.append(Accessor(bufferView=vi,byteOffset=0,componentType=5126,count=len(b['v']),type='VEC4'))
            mesh.primitives[0].attributes.COLOR_0=ai
        gltf.buffers[0].byteLength=len(blob);gltf.set_binary_blob(bytes(blob));gltf.save_binary(str(path));temp.unlink()

def poly_mesh(poly,z,thickness=.24):
    """Extrude a Shapely polygon, retaining holes and concave edges."""
    from shapely import constrained_delaunay_triangles
    verts=[];faces=[]
    parts=list(poly.geoms) if poly.geom_type=='MultiPolygon' else [poly]
    def tri(points):
        k=len(verts);verts.extend(points);faces.append((k,k+1,k+2))
    for p in parts:
        for t in constrained_delaunay_triangles(p).geoms:
            q=list(t.exterior.coords)[:3]
            e1=np.array(q[1])-q[0];e2=np.array(q[2])-q[0]
            cross=e1[0]*e2[1]-e1[1]*e2[0]
            if cross<0:q.reverse()
            tri([(x,y,z) for x,y in q]);tri([(x,y,z-thickness) for x,y in q[::-1]])
        from shapely.geometry.polygon import orient
        p=orient(p,sign=1)
        for ring in [p.exterior,*p.interiors]:
            for a,b in zip(ring.coords,list(ring.coords)[1:]):
                tri([(a[0],a[1],z),(a[0],a[1],z-thickness),(b[0],b[1],z-thickness)])
                tri([(a[0],a[1],z),(b[0],b[1],z-thickness),(b[0],b[1],z)])
    return np.array(verts),np.array(faces)
