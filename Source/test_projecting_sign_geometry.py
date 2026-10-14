"""Portable component-range, cloth topology/UV, and GLB semantic negatives."""
import copy
import unittest
from pathlib import Path
import numpy as np
from projecting_sign_geometry_scope import recovered_component,cloth_diagnostic
from audit_projecting_sign_glb import activated_material,ACTIVATED_MATERIALS,BEFORE_NAME,BEFORE_SHA256
import projecting_sign_contract as c

class ComponentGeometryTests(unittest.TestCase):
 def setUp(self):
  self.k=('Shops/S02/ProjectingSigns/NoodleGuildAssembly','Noren3')
  self.b=dict(vertices=np.array([[0,0,0],[1,0,0],[0,0,1],[1,0,1]],float),faces=np.array([[0,1,2],[1,3,2]],int),uv=np.array([[0,0],[4,0],[0,4],[4,4]],float))
  self.comp=dict(role='static_cloth_pennant',localBounds=[[0,0,0],[1,0,1]],dimensions=[1,0,1],triangles=2,sourceVertexCount=4,semantic='GuildPennant',ranges=[dict(key=list(self.k),vertexStart=0,vertexCount=4,triangleStart=0,triangleCount=2)])
 def recover(self,comp=None):
  coverage={self.k:np.zeros(2,np.int16)};r=recovered_component(self.comp if comp is None else comp,{self.k:self.b},np.zeros(3),np.eye(3),coverage);return r,coverage
 def test_real_triangle_slice_coverage(self):
  (tri,slices,errors),coverage=self.recover();self.assertFalse(errors);self.assertEqual(tri.shape,(2,3,3));self.assertTrue(np.all(coverage[self.k]==1))
 def test_native_recovery_does_not_address_source_vertex_ranges(self):
  # UV repair can move corners beyond the original source component span.
  b=self.b;original=b['vertices'].copy();b['vertices']=np.vstack([original,original]);b['faces']=b['faces']+4
  (tri,_,errors),_=self.recover();self.assertFalse(errors);np.testing.assert_array_equal(tri,original[np.array([[0,1,2],[1,3,2]])])
 def test_unknown_key_and_out_of_bounds_reject(self):
  for field,value in [('key',['Unknown','Noren3']),('triangleStart',1),('triangleCount',3),('vertexCount',-1),('triangleStart',True)]:
   q=copy.deepcopy(self.comp);q['ranges'][0][field]=value;self.assertTrue(self.recover(q)[0][2],field)
 def test_missing_added_field_and_wrong_source_count_reject(self):
  q=copy.deepcopy(self.comp);q['unexpected']=True;self.assertTrue(self.recover(q)[0][2])
  q=copy.deepcopy(self.comp);q['sourceVertexCount']=5;self.assertTrue(self.recover(q)[0][2])
 def test_overlap_remains_visible_in_coverage_not_silently_removed(self):
  q=copy.deepcopy(self.comp);q['ranges']*=2;q['triangles']=4;q['sourceVertexCount']=8
  (_,_,errors),coverage=self.recover(q);self.assertFalse(errors);self.assertTrue(np.all(coverage[self.k]==2))
 def box(self):
  from world_geometry import Geometry
  g=Geometry();g.box([0,0,0],[.3,.004,.4],'Cloth');b=next(iter(g.batches.values()));v=np.asarray(b['v']);f=np.asarray(b['f']);uv=4*v[:,[0,2]];return v,f,uv
 def test_closed_outward_cloth_and_four_repeat_uv(self):
  d=cloth_diagnostic(*self.box());self.assertTrue(d['closed']);self.assertTrue(d['consistentWinding']);self.assertTrue(d['allComponentsOutward']);np.testing.assert_allclose(d['uvRepeatsPerMetreMedians'],[4,4])
 def test_missing_or_inward_cloth_faces_reject(self):
  v,f,uv=self.box();self.assertFalse(cloth_diagnostic(v,f[:-1],uv)['closed']);d=cloth_diagnostic(v,f[:,::-1],uv);self.assertTrue(d['closed']);self.assertFalse(d['allComponentsOutward'])
 def test_zero_uv_is_not_four_repeat_weave(self):
  v,f,uv=self.box();self.assertEqual(cloth_diagnostic(v,f,np.zeros_like(uv))['uvRepeatsPerMetreMedians'],[0,0])
 def test_exact_two_existing_material_activation_semantics(self):
  old=c._load(BEFORE_NAME,BEFORE_SHA256)
  self.assertEqual(ACTIVATED_MATERIALS,('Noren1','Noren3'));self.assertNotIn('Noren1',old['materials']);self.assertNotIn('Noren3',old['materials'])
  a=activated_material('Noren1',old);b=activated_material('Noren3',old)
  self.assertFalse(a['doubleSided']);self.assertEqual(a['normalTexture']['scale'],1);self.assertEqual(a['pbrMetallicRoughness']['roughnessFactor'],1)
  self.assertEqual(a['normalTexture'],b['normalTexture']);self.assertEqual(a['occlusionTexture'],b['occlusionTexture']);self.assertNotEqual(a['pbrMetallicRoughness']['baseColorFactor'],b['pbrMetallicRoughness']['baseColorFactor'])
  with self.assertRaises(KeyError):activated_material('Noren0',old)
 def test_old_glb_capture_covers_even_unused_accessors(self):
  old=c._load(BEFORE_NAME,BEFORE_SHA256);self.assertEqual(len(old['allAccessors']),4576);self.assertEqual(len(old['meshes']),1107)

if __name__=='__main__':unittest.main(verbosity=2)
