"""Synthetic mutation tests do not constitute source/art approval."""
import copy
import unittest
from unittest.mock import patch
import rpg_identity_contract as c
import rpg_runtime_compatibility as runtime

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=c.load_before()
        cls.rows=cls.before['rows']
        cls.manifest=copy.deepcopy(cls.before['manifest'])
        cls.manifest['version']=c.VERSION
        cls.manifest['features'].update({f:False for f in c.FLAGS})
        cls.manifest['meshOptimization']['cityCaps']['builderSha256']=runtime.load_oracle()['dependencies'][runtime.BUILDER]
        cls.oracle={'variants':{'00':{'rows':cls.rows,'manifest':cls.manifest}}}
    def test_unfrozen_fails_closed(self):
        with patch.object(c,'ORACLE_SHA256','UNFROZEN_TEST'):
            with self.assertRaisesRegex(ValueError,'independently accepted'):c.load_oracle()
    def test_legacy_untouched(self):
        m=self.before['manifest'];r=self.rows
        self.assertFalse(c.requested(m));self.assertEqual(c.normalize_summaries(r,m),(r,m,[],None))
    def test_false_false_scope(self):
        ok,r=c.audit_scope(self.rows,self.manifest);self.assertTrue(ok,r)
    def test_both_literal_flags_required(self):
        for flag in c.FLAGS:
            for invalid in (None,0,1,'true',[],{}):
                m=copy.deepcopy(self.manifest);m['features'][flag]=invalid
                self.assertTrue(c.validate_gate(m),(flag,invalid))
            m=copy.deepcopy(self.manifest);del m['features'][flag];self.assertTrue(c.validate_gate(m))
    def test_all_variants_new_version(self):
        for version in ('2.16.0',None,2.17):
            m=copy.deepcopy(self.manifest);m['version']=version;self.assertTrue(c.validate_gate(m))
    def test_disabled_payload_rejected(self):
        for field in ('shopRpgIdentity','venueLighting'):
            m=copy.deepcopy(self.manifest);m[field]={};self.assertTrue(c.validate_gate(m))
    def test_no_metadata_only_normalization(self):
        m=copy.deepcopy(self.manifest);m['lights'][0]['strength']+=.01
        with patch.object(c,'load_oracle',return_value=self.oracle):
            r,actual,errors,_=c.normalize_summaries(self.rows,m)
        self.assertTrue(errors);self.assertIs(r,self.rows);self.assertIs(actual,m)
    def test_exact_record_order(self):
        rows=copy.deepcopy(self.rows);rows[0],rows[1]=rows[1],rows[0]
        ok,_=c.validate_summaries(rows,self.manifest,oracle=self.oracle);self.assertFalse(ok)
    def test_every_summary_field_authenticated(self):
        for field in c.FIELDS:
            rows=copy.deepcopy(self.rows);rows[0][field]='tamper'
            ok,_=c.validate_summaries(rows,self.manifest,oracle=self.oracle);self.assertFalse(ok,field)
    def test_every_array_scope_protected(self):
        for attr in ('vertices','uv','faces','colors'):
            rows=copy.deepcopy(self.rows);rows[0]['arraySha256'][attr]='0'*64
            ok,_=c.audit_scope(rows,self.manifest);self.assertFalse(ok,attr)
    def test_unrelated_metadata_scope_protected(self):
        for field in ('stations','solidBoxes','lights','guards','floorTests','wallTests','spawns','teleports'):
            m=copy.deepcopy(self.manifest);m[field]=[]
            try:ok,_=c.audit_scope(self.rows,m)
            except (KeyError,TypeError,IndexError):ok=False
            self.assertFalse(ok,field)
    def test_exact_json_types(self):
        m=copy.deepcopy(self.manifest);m['visualMeshCount']=float(m['visualMeshCount'])
        ok,_=c.validate_summaries(self.rows,m,oracle=self.oracle);self.assertFalse(ok)
    def test_projection_after_authentication_only(self):
        with patch.object(c,'load_oracle',return_value=self.oracle):
            rows,m,errors,detail=c.normalize_summaries(self.rows,self.manifest)
        self.assertFalse(errors);self.assertEqual(m,self.before['manifest'])
        self.assertEqual(rows,[{k:r[k] for k in c.FIELDS} for r in self.before['rows']])
        self.assertIsNot(m,self.before['manifest'])
    def test_bad_counts_fail_before_loading_oracle(self):
        with patch.object(c,'load_oracle',side_effect=AssertionError('Wrong actual counts must fail before loading art')):
            for rows in (self.rows[:-1],self.rows+[self.rows[0]]):
                ok,_=c.validate_summaries(rows,self.manifest);self.assertFalse(ok)
            for field in ('visualMeshCount','visualTriangles'):
                for value in (True,float(self.manifest[field]),None,'1106'):
                    m=copy.deepcopy(self.manifest);m[field]=value
                    ok,_=c.validate_summaries(self.rows,m);self.assertFalse(ok)
    def test_wrong_rows_do_not_hash_large_manifest(self):
        rows=copy.deepcopy(self.rows);rows[0]['attributesAndIndicesSha256']='0'*64
        digest=c.digest
        def rows_only(value):
            if isinstance(value,dict):raise AssertionError('Rejected rows must not hash manifest')
            return digest(value)
        with patch.object(c,'digest',side_effect=rows_only):
            ok,_=c.validate_summaries(rows,self.manifest,oracle=self.oracle)
        self.assertFalse(ok)
    def test_valid_rows_still_hash_full_manifest(self):
        m=copy.deepcopy(self.manifest);m['lights'][88]['strength']+=.001
        with patch.object(c,'digest',wraps=c.digest) as called:
            ok,_=c.validate_summaries(self.rows,m,oracle=self.oracle)
        self.assertFalse(ok)
        self.assertTrue(any(call.args[0] is m for call in called.call_args_list))

    def test_no_production_inverse(self):
        from pathlib import Path
        source=Path(c.__file__).read_text()
        self.assertNotIn('import rpg_identity_test_fixture',source)
        self.assertNotIn('np.load',source)

if __name__=='__main__':unittest.main(verbosity=2)
