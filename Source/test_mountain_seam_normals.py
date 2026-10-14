"""Source/export parity evidence only. Does NOT execute Unity or C# runtime."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
from pygltflib import GLTF2
from mountain_detail_test_fixture import frozen_arrays
from mountain_detail_contract import KEYS
from mountain_seam_normals import seam_normal_overrides,_kernel
from world_geometry import Geometry
from test_snow_deposition import geometry,raw
from mountain_detail import apply_mountain_detail
from fantasy_landscape import apply_snow_deposition
ROOT=Path(__file__).resolve().parents[1]


def glb_arrays(path):
 g=GLTF2().load(str(path));blob=g.binary_blob();out={}
 def data(index):
  a=g.accessors[index];v=g.bufferViews[a.bufferView];dtype={5121:'u1',5125:'<u4',5126:'<f4'}[a.componentType];width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a.type]
  return np.frombuffer(blob,dtype=dtype,count=a.count*width,offset=(v.byteOffset or 0)+(a.byteOffset or 0)).reshape(a.count,width).copy()
 for m in g.meshes:
  p=m.primitives[0];out[m.name]={f:data(getattr(p.attributes,f)) for f in ['POSITION','NORMAL','TEXCOORD_0','COLOR_0']};out[m.name]['INDICES']=data(p.indices)
 return out

class MountainSeamNormalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.batches=frozen_arrays('after_snow');cls.overrides,cls.stats=seam_normal_overrides(cls.batches)

 def test_exact_scope_and_unit_finite_normals(self):
  self.assertEqual(self.stats['inputBatches'],12);self.assertEqual(self.stats['eligibleSharedPositions'],1765);self.assertEqual(self.stats['excludedSharpSeamPositions'],36);self.assertEqual(self.stats['allSharpEdgeCount'],89);self.assertEqual(self.stats['changedNormalSlots'],3637)
  shared={}
  for b in self.batches:
   ids,normals=self.overrides[(b['group'],b['material'])]
   self.assertTrue(np.isfinite(normals).all());np.testing.assert_allclose(np.linalg.norm(normals,axis=1),1,atol=1e-7)
   for i,n in zip(ids,normals):
    p=tuple(b['vertices'][i]);
    if p in shared:np.testing.assert_array_equal(n,shared[p])
    shared[p]=n
  self.assertEqual(len(shared),1765)

 def test_batch_face_vertex_permutation_and_cyclic_order_determinism(self):
  bykey={}
  for b in self.batches:
   key=(b['group'],b['material']);ids,n=self.overrides[key];bykey[key]={tuple(b['vertices'][i]):v for i,v in zip(ids,n)}
  random=np.random.default_rng(721);permuted=[]
  for b in self.batches[::-1]:
   new=copy.deepcopy(b);order=random.permutation(len(b['vertices']));inverse=np.argsort(order);new['vertices']=b['vertices'][order];f=inverse[b['faces']];f=f[random.permutation(len(f))]
   for i in range(len(f)):f[i]=np.roll(f[i],i%3)
   new['faces']=f.astype(np.uint32);permuted.append(new)
  result,stats=_kernel(permuted)
  self.assertEqual(stats,self.stats)
  for b in permuted:
   key=(b['group'],b['material']);ids,n=result[key]
   for i,v in zip(ids,n):np.testing.assert_array_equal(v,bykey[key][tuple(b['vertices'][i])])
  # Production admission still rejects reordered native payloads; only the
  # mathematical private kernel accepts this synthetic invariance fixture.
  with self.assertRaises(ValueError):seam_normal_overrides(permuted)

 def test_unapproved_and_degenerate_inputs_are_rejected(self):
  with self.assertRaises(ValueError):seam_normal_overrides(self.batches[:-1])
  bad=copy.deepcopy(self.batches);bad[0]['vertices'][0,2]+=.01
  with self.assertRaises(ValueError):seam_normal_overrides(bad)
  for mode in ['zero','nonfinite','index']:
   bad=copy.deepcopy(self.batches)
   if mode=='zero':bad[0]['faces'][0]=[0,0,0]
   elif mode=='nonfinite':bad[0]['vertices'][0,0]=np.nan
   else:bad[0]['faces'][0,0]=len(bad[0]['vertices'])
   with self.assertRaises(ValueError):_kernel(bad)

 def test_glb_changes_only_eligible_normals_and_native_unchanged(self):
  g=geometry();apply_mountain_detail(g);apply_snow_deposition(g)
  g.group='Unrelated/Sentinel';g.material('Sentinel',(.3,.2,.1));g.add([(0,0,0),(1,0,0),(0,1,1)],[(0,1,2)],'Sentinel',[(0,0),(1,0),(0,1)])
  g.compact();g.bake_mood([]);original={k:raw(b) for k,b in g.batches.items()}
  with tempfile.TemporaryDirectory(prefix='mountain-normal-proof-') as d:
   d=Path(d);g.save_glb(d/'before.glb',ROOT/'Assets/TreeTopYokocho/Textures');g.save_glb(d/'after.glb',ROOT/'Assets/TreeTopYokocho/Textures',mountain_seam_normals=True)
   before,after=glb_arrays(d/'before.glb'),glb_arrays(d/'after.glb');self.assertEqual(set(before),set(after));changed=0
   for name,attrs in before.items():
    key=tuple(name.split('__'))
    for field in ('POSITION','TEXCOORD_0','COLOR_0','INDICES'):np.testing.assert_array_equal(attrs[field],after[name][field])
    actual=after[name]['NORMAL']
    if key not in self.overrides:np.testing.assert_array_equal(attrs['NORMAL'],actual);continue
    ids,n=self.overrides[key];mask=np.ones(len(actual),bool);mask[ids]=False;np.testing.assert_array_equal(attrs['NORMAL'][mask],actual[mask]);converted=n[:,[0,2,1]].copy();converted[:,2]*=-1;np.testing.assert_array_equal(actual[ids],converted);changed+=int(np.sum(np.any(attrs['NORMAL']!=actual,axis=1)))
   self.assertGreater(changed,3000)
  self.assertEqual(original,{k:raw(b) for k,b in g.batches.items()})
  with self.assertRaises(ValueError):g.save_glb(ROOT/'Proof/should_not_exist.glb',ROOT/'Assets/TreeTopYokocho/Textures',mountain_seam_normals='true')

 def test_source_unity_reflection_winding_and_tangent_handedness(self):
  S=np.array([[1,0,0],[0,0,1],[0,1,0]],float);R=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
  count=0
  for batch in self.batches:
   v=batch['vertices'].astype(float);uv=batch['uv'].astype(float);f=batch['faces'];mesh=trimesh.Trimesh(v,f,process=False);normals=mesh.vertex_normals.copy();ids,n=self.overrides[(batch['group'],batch['material'])];normals[ids]=n
   for indices in f[::max(1,len(f)//50)]:
    p=v[indices];u=uv[indices];e1,e2=p[1]-p[0],p[2]-p[0];du1,du2=u[1]-u[0],u[2]-u[0];det=du1[0]*du2[1]-du1[1]*du2[0]
    if abs(det)<1e-10:continue
    tangent=(e1*du2[1]-e2*du1[1])/det;bitangent=(e2*du1[0]-e1*du2[0])/det;n=normals[indices[0]];tangent-=n*np.dot(n,tangent);tangent/=np.linalg.norm(tangent);w=np.sign(np.dot(np.cross(n,tangent),bitangent))
    for matrix,sign in [(S,-1),(R,1)]:
     nn,tt,bb=matrix@n,matrix@tangent,matrix@bitangent
     self.assertAlmostEqual(float(nn@tt),0,places=6);self.assertEqual(np.sign(np.dot(np.cross(nn,tt),bb)),sign*w)
     q=p@matrix.T
     winding=[0,2,1] if sign<0 else [0,1,2];sourceface=np.cross(e1,e2);destface=np.cross(q[winding[1]]-q[0],q[winding[2]]-q[0]);np.testing.assert_allclose(destface,matrix@sourceface,atol=1e-8)
    # Reconstructing source XYZ and indices from imported Unity is exact.
    np.testing.assert_array_equal((v[indices]@S.T)@S,v[indices]);count+=1
  self.assertGreater(count,400)

 def test_csharp_syntax_exact_hashes_constants_and_scope_guards(self):
  import tree_sitter_c_sharp
  from tree_sitter import Language,Parser
  path=ROOT/'Assets/TreeTopYokocho/Editor/MountainSeamNormals.cs';source=path.read_bytes();parser=Parser(Language(tree_sitter_c_sharp.language()));tree=parser.parse(source);self.assertFalse(tree.root_node.has_error)
  text=source.decode();self.assertIn('CreaseCosine = 0.5735764363510462',text);self.assertIn('triangles.Sort()',text);self.assertIn('owners[i].Count<2',text);self.assertIn('crease.Contains(i)',text);self.assertIn('new Position(v[i].x,v[i].z,v[i].y)',text);self.assertIn('int a=f[i],b=f[i+2],c=f[i+1]',text)
  from mountain_detail_contract import load_oracle
  for row in load_oracle()['variants']['after_plain']:self.assertIn(row['geometrySha256'],text)
  self.assertNotIn('mesh.vertices =',text);self.assertNotIn('mesh.triangles =',text);self.assertNotIn('mesh.colors',text);self.assertNotIn('mesh.uv',text)
  builder=ROOT/'Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs';self.assertFalse(parser.parse(builder.read_bytes()).root_node.has_error)
  builder_text=builder.read_text();self.assertIn('!collision && !deferMountainAsset',builder_text);self.assertIn('ModelImporterMeshCompression.Off',builder_text)
  apply_pos=builder_text.index('MountainSeamNormals.Apply(mountainMeshes)');off_pos=builder_text.index('ModelImporterMeshCompression.Off',apply_pos);create_pos=builder_text.index('AssetDatabase.CreateAsset(mesh, mountainAssetPaths[key])',apply_pos);self.assertLess(apply_pos,off_pos);self.assertLess(off_pos,create_pos)
  self.assertIn('MountainSeamNormals.IsApproved(group, material)',builder_text)

if __name__=='__main__':unittest.main(verbosity=2)
