"""Synthetic negative cases never approve S05 art; frozen evidence is separate."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
import s05_pendant_contract as c

class PendantContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.prior=c.before();cls.rows=copy.deepcopy(cls.prior['rows']);old=next(r for r in cls.rows if c.key(r)==c.OLD_KEY)
  old.update(vertices=146,triangles=76,geometrySha256='1'*64,attributesAndIndicesSha256='2'*64)
  added=copy.deepcopy(old);added.update(material='DarkTimber',vertices=672,triangles=320,geometrySha256='3'*64,attributesAndIndicesSha256='4'*64);cls.rows.append(added)
  cls.manifest=copy.deepcopy(cls.prior['manifest']);m=cls.manifest;m['version']=c.VERSION;m['features'][c.FEATURE]=True;m['visualMeshCount']+=1;m['visualTriangles']+=144
  m['altitudeProfile']['visuals']['transformedBatches']+=1;m['altitudeProfile']['visuals']['transformedVertices']+=288
  for s in m['shopPersonality']['shops']:
   if s['id'] in c.FOOD_IDS:s['sourceSha256']='0'*64
  m['s05PendantRefinement']=dict(schema=1,version=c.VERSION,baselineVersion='2.17.0',baselineNativeSha256=c.BEFORE_NATIVE_SHA256,sourceSha256='0'*64,capCount=4,stileCount=12,addedTriangles=144)
  cls.pin=dict(rowsSha256=c.digest([{f:r[f] for f in c.FIELDS} for r in cls.rows]),manifestSha256=c.digest(m))
 def test_legacy_no_flag_untouched(self):
  rows,m=self.prior['rows'],self.prior['manifest'];self.assertFalse(c.requested(m));self.assertEqual(c.normalize_summaries(rows,m),(rows,m,[],None))
 def test_true_only_literal_gate(self):
  for value in (False,None,0,1,1.0,'true',[],{}):
   m=copy.deepcopy(self.manifest);m['features'][c.FEATURE]=value;self.assertTrue(c.validate_gate(m),value)
  m=copy.deepcopy(self.manifest);del m['features'][c.FEATURE];self.assertTrue(c.validate_gate(m))
 def test_prior_state11_and_version_required(self):
  for f in ('shop_personality','shop_rpg_identity','venue_lighting_identity'):
   m=copy.deepcopy(self.manifest);m['features'][f]=False;self.assertTrue(c.validate_gate(m))
  m=copy.deepcopy(self.manifest);m['version']='2.17.0';self.assertTrue(c.validate_gate(m))
 def test_unfrozen_fails_closed(self):
  with patch.object(c,'ORACLE_SHA256','UNFROZEN_TEST'):
   with self.assertRaisesRegex(ValueError,'independently accepted'):c.load_oracle()
 def test_synthetic_exact_current_admission(self):
  ok,report=c.validate_summaries(self.rows,self.manifest,oracle=self.pin);self.assertTrue(ok,report)
 def test_counts_reject_before_oracle(self):
  with patch.object(c,'load_oracle',side_effect=AssertionError('Invalid count must fail before after loading')):
   for rows in (self.rows[:-1],self.rows+[self.rows[0]]):self.assertFalse(c.validate_summaries(rows,self.manifest)[0])
   for name in ('visualMeshCount','visualTriangles'):
    m=copy.deepcopy(self.manifest);m[name]=float(m[name]);self.assertFalse(c.validate_summaries(self.rows,m)[0])
 def test_every_summary_field_rejected(self):
  for field in c.FIELDS:
   rows=copy.deepcopy(self.rows);rows[0][field]='tamper';self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0],field)
 def test_order_and_extra_key_rejected(self):
  rows=copy.deepcopy(self.rows);rows[0],rows[1]=rows[1],rows[0];self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0])
  rows=copy.deepcopy(self.rows);rows[-1]['group']+='Hidden';self.assertFalse(c.validate_summaries(rows,self.manifest,oracle=self.pin)[0])
 def test_metadata_exact_json_types(self):
  m=copy.deepcopy(self.manifest);m['s05PendantRefinement']['capCount']=4.0;self.assertFalse(c.validate_summaries(self.rows,m,oracle=self.pin)[0])
 def test_current_metadata_cannot_be_hidden(self):
  for field in ('stations','solidBoxes','lights','materials','venueLighting','shopRpgIdentity'):
   m=copy.deepcopy(self.manifest);m[field]=[]
   with patch.object(c,'load_oracle',return_value=self.pin):
    rows,actual,errors,_=c.normalize_summaries(self.rows,m)
   self.assertTrue(errors);self.assertIs(rows,self.rows);self.assertIs(actual,m)
 def test_scope_positive_and_unrelated_arrays(self):
  self.assertTrue(c.audit_scope(self.rows,self.manifest,prior=self.prior)[0])
  rows=copy.deepcopy(self.rows);rows[0]['arraySha256']['colors']='0'*64;self.assertFalse(c.audit_scope(rows,self.manifest,prior=self.prior)[0])
 def test_no_expanded_counter_exemption(self):
  for field in ('normalUvRepairs','visualTriangles'):
   m=copy.deepcopy(self.manifest);m[field]+=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
  m=copy.deepcopy(self.manifest);m['altitudeProfile']['visuals']['transformedVertices']+=1;self.assertFalse(c.audit_scope(self.rows,m,prior=self.prior)[0])
 def test_project_only_after_full_authentication(self):
  with patch.object(c,'load_oracle',return_value=self.pin):
   rows,m,errors,_=c.normalize_summaries(self.rows,self.manifest)
  self.assertFalse(errors);self.assertEqual(m,self.prior['manifest']);self.assertEqual(rows,[{f:r[f] for f in c.FIELDS} for r in self.prior['rows']])
 def test_no_production_inverse(self):
  source=Path(c.__file__).read_text();self.assertNotIn('import s05_pendant_test_fixture',source);self.assertNotIn('np.load',source)
if __name__=='__main__':unittest.main(verbosity=2)
