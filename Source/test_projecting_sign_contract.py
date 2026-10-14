"""Independent synthetic adversarial contract tests; never approve new art."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
import projecting_sign_contract as c

class ProjectingSignContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.prior=c.before();cls.keys=tuple((f'Shops/S{i:02d}/ProjectingSigns/Emblem','Iron') for i in range(1,9))
  cls.rows=copy.deepcopy(cls.prior['rows']);cls.manifest=copy.deepcopy(cls.prior['manifest']);m=cls.manifest
  venues=[]
  for i,k in enumerate(cls.keys):
   row=dict(group=k[0],material=k[1],vertices=6,triangles=2,geometrySha256=str(i+1)*64,attributesAndIndicesSha256=str(i+1)*64,arraySha256={a:str(i+1)*64 for a in ('vertices','uv','colors','faces')});cls.rows.append(row)
   venues.append(dict(shop=f'S{i+1:02d}',motif=c.MOTIFS[i],keys=[list(k)],sourceVertexCount=6,triangleCount=2,batchCount=1))
  m['version']=c.VERSION;m['features'][c.FEATURE]=True;m['visualMeshCount']+=8;m['visualTriangles']+=16
  m['altitudeProfile']['visuals']['transformedBatches']+=8;m['altitudeProfile']['visuals']['transformedVertices']+=48
  m[c.METADATA]=dict(schema=1,version=c.VERSION,baselineVersion='2.18.0',baselineNativeSha256=c.BEFORE_NATIVE_SHA256,sourceSha256='0'*64,venues=venues)
  cls.pin=dict(rowsSha256=c.digest([{f:r[f] for f in c.FIELDS} for r in cls.rows]),manifestFieldHashes={k:c.digest(v) for k,v in m.items()},manifestFieldOrder=sorted(m,key=lambda k:(len(c.encoded(m[k])),k)))
 def setUp(self):self.roster=patch.object(c,'KEYS',self.keys);self.roster.start()
 def tearDown(self):self.roster.stop()
 def clone(self):return copy.deepcopy(self.manifest)
 def test_accepted_before_is_exact_v218(self):
  self.assertEqual(len(self.prior['rows']),1107);self.assertEqual(self.prior['manifest']['version'],'2.18.0');self.assertEqual(self.prior['nativeSha256'],c.BEFORE_NATIVE_SHA256)
 def test_legacy_no_flag_untouched(self):
  r,m=self.prior['rows'],self.prior['manifest'];self.assertFalse(c.requested(m));self.assertEqual(c.normalize_summaries(r,m),(r,m,[],None))
 def test_false_missing_nonliteral_features_fail(self):
  for value in (False,None,0,1,1.0,'true',[],{}):
   m=self.clone();m['features'][c.FEATURE]=value;self.assertTrue(c.validate_gate(m),value)
  m=self.clone();del m['features'][c.FEATURE];self.assertTrue(c.validate_gate(m))
  for value in (False,None,[],1):
   m=self.clone();m['features']=value;self.assertTrue(c.validate_gate(m))
 def test_version_and_prior_exact_true_state(self):
  for f in ('shop_personality','shop_rpg_identity','venue_lighting_identity','s05_pendant_refinement'):
   for value in (False,1,None):
    m=self.clone();m['features'][f]=value;self.assertTrue(c.validate_gate(m))
  for value in ('2.18.0','2.20.0',None):
   m=self.clone();m['version']=value;self.assertTrue(c.validate_gate(m))
 def test_provenance_schema_rejects_missing_extra_wrong_type(self):
  for field in self.manifest[c.METADATA]:
   m=self.clone();del m[c.METADATA][field];self.assertTrue(c.validate_gate(m),field)
  m=self.clone();m[c.METADATA]['extra']=True;self.assertTrue(c.validate_gate(m))
  for value in (True,1.0,'1'):
   m=self.clone();m[c.METADATA]['schema']=value;self.assertTrue(c.validate_gate(m))
 def test_outer_rpg_routing_detects_orphaned_new_feature_metadata_or_version(self):
  import rpg_identity_contract as rpg
  for m in ({'features':{c.FEATURE:False}},{c.METADATA:{}},{'version':c.VERSION}):
   self.assertTrue(rpg.requested(m));self.assertTrue(rpg.validate_gate(m))
 def test_unfrozen_art_fails_closed(self):
  with patch.object(c,'ORACLE_SHA256','UNFROZEN_TEST'):
   with self.assertRaisesRegex(ValueError,'independently accepted'):c.load_oracle()
 def test_synthetic_exact_admission(self):self.assertTrue(c.validate_summaries(self.rows,self.manifest,oracle=self.pin)[0])
 def test_bad_counts_fail_before_oracle(self):
  with patch.object(c,'load_oracle',side_effect=AssertionError('Bad counts must fail before after-oracle loading')):
   for rows in (self.rows[:-1],self.rows+[self.rows[0]]):self.assertFalse(c.validate_summaries(rows,self.manifest)[0])
   for f in ('visualMeshCount','visualTriangles'):
    m=self.clone();m[f]=float(m[f]);self.assertFalse(c.validate_summaries(self.rows,m)[0])
 def test_every_summary_field_existing_and_added_rejected(self):
  for index in (0,-1):
   for field in c.FIELDS:
    rows=copy.deepcopy(self.rows);rows[index][field]='tamper';self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0],(index,field))
 def test_invalid_rows_fail_without_any_metadata_hash(self):
  rows=copy.deepcopy(self.rows);rows[0]['geometrySha256']='f'*64
  with patch.object(c,'_metadata_error',side_effect=AssertionError('Invalid row must fail before metadata hashing')):self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0])
 def test_order_duplicate_and_unknown_key_rejected(self):
  rows=copy.deepcopy(self.rows);rows[0],rows[1]=rows[1],rows[0];self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0])
  rows=copy.deepcopy(self.rows);rows[-1]['group']+='Hidden';self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0])
  rows=copy.deepcopy(self.rows);rows[-1]=copy.deepcopy(rows[-2]);self.assertFalse(c.audit_scope(rows,self.manifest,prior=self.prior)[0])
 def test_current_high_impact_metadata_cannot_hide_under_projection(self):
  for f in ('stations','solidBoxes','lights','materials','venueLighting','shopRpgIdentity','shopPersonality','s05PendantRefinement'):
   m=self.clone();m[f]=[]
   with patch.object(c,'load_oracle',return_value=self.pin):r,observed,errors,_=c.normalize_summaries(self.rows,m)
   self.assertTrue(errors,f);self.assertIs(r,self.rows);self.assertIs(observed,m)
 def test_small_field_change_does_not_hash_crown_geometry(self):
  m=self.clone();m['testedInUnity']=True;real=c.digest
  def guard(v):
   if v is m['crownStairs']:raise AssertionError('Small invalid field should fail before large crown field')
   return real(v)
  with patch.object(c,'digest',side_effect=guard):self.assertFalse(c.validate_metadata(m,oracle=self.pin)[0])
 def test_exact_numeric_types_and_metadata_roster(self):
  m=self.clone();m['safetyHeight']=8;self.assertFalse(c.validate_metadata(m,oracle=self.pin)[0])
  m=self.clone();m['Unreviewed']=[];self.assertFalse(c.validate_metadata(m,oracle=self.pin)[0])
 def test_scope_preserves_every_old_array_field(self):
  self.assertTrue(c.audit_scope(self.rows,self.manifest,prior=self.prior)[0])
  for attr in ('vertices','uv','colors','faces'):
   rows=copy.deepcopy(self.rows);rows[0]['arraySha256'][attr]='0'*64;self.assertFalse(c.audit_scope(rows,self.manifest,prior=self.prior)[0],attr)
 def test_scope_rejects_old_order_or_source_provenance(self):
  rows=copy.deepcopy(self.rows);rows[0],rows[1]=rows[1],rows[0];self.assertFalse(c.audit_scope(rows,self.manifest,prior=self.prior)[0])
  m=self.clone();m['shopPersonality']['shops'][4]['sourceSha256']='f'*64;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
 def test_exact_counter_algebra_not_a_counter_exemption(self):
  for field in ('normalUvRepairs','visualTriangles'):
   m=self.clone();m[field]+=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
  for field in ('transformedVertices','transformedBatches','retiledVertices','excludedBatches'):
   m=self.clone();m['altitudeProfile']['visuals'][field]+=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
  m=self.clone();m['meshOptimization']['unused']['removedVertices']+=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
 def test_compaction_cannot_rewrite_old_records(self):
  m=self.clone();m['meshOptimization']['unused']['batches'][0]['afterVertices']-=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
 def test_exact_added_venue_inventory(self):
  for field,value in [('shop','S09'),('motif','unowned'),('sourceVertexCount',7),('triangleCount',3),('batchCount',2)]:
   m=self.clone();m[c.METADATA]['venues'][0][field]=value;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0],field)
 def test_projection_only_after_current_authentication(self):
  with patch.object(c,'load_oracle',return_value=self.pin):rows,m,errors,_=c.normalize_summaries(self.rows,self.manifest)
  self.assertFalse(errors);self.assertEqual(rows,[{f:r[f] for f in c.FIELDS} for r in self.prior['rows']]);self.assertEqual(m,self.prior['manifest'])
 def test_no_production_inverse_or_shop_prefix_exemption(self):
  source=Path(c.__file__).read_text();self.assertNotIn('projecting_sign_test_fixture',source);self.assertNotIn('np.load',source);self.assertNotIn("startswith('Shops/",source)
if __name__=='__main__':unittest.main(verbosity=2)
