"""Portable malicious source-mutation tests; synthetic pins are never release art."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import rpg_runtime_compatibility as c

class RuntimeTests(unittest.TestCase):
    def test_immutable_prior_roster(self):
        before=c.baseline_runtime()
        self.assertEqual(before[c.BUILDER],c.LEGACY_BUILDER_SHA256)
        self.assertNotIn(c.ADDED_RUNTIME[0],before)
        self.assertEqual(sum(p.endswith('.cs') for p in before),4)
    def test_unfrozen_fails_closed(self):
        with patch.object(c,'ORACLE_SHA256','UNFROZEN_TEST'):
            with self.assertRaisesRegex(ValueError,'source-reviewed'):c.load_oracle()
    def test_every_file_and_new_roster_checked(self):
        before=c.baseline_runtime()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);deps={}
            for rel in sorted(set(before)|set(c.ADDED_RUNTIME)):
                path=root/rel;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('synthetic only '+rel);deps[rel]=c.sha(path.read_bytes())
            profile=root/c.PROFILE;profile.parent.mkdir(parents=True,exist_ok=True)
            profile.write_text('synthetic profile')
            pin=dict(dependencies=deps)
            with patch.object(c,'LEGACY_SHOP_PROFILE_SHA256',c.sha(profile.read_bytes())):
                self.assertEqual(c.verify_runtime(root,oracle=pin),deps[c.BUILDER])
                for rel in deps:
                    path=root/rel;old=path.read_bytes();path.write_bytes(old+b'tamper')
                    with self.subTest(path=rel):
                        with self.assertRaises(ValueError):c.verify_runtime(root,oracle=pin)
                    path.write_bytes(old)
                extra=root/'Assets/TreeTopYokocho/Editor/Unreviewed.cs';extra.write_text('extra')
                with self.assertRaisesRegex(ValueError,'roster'):c.verify_runtime(root,oracle=pin)
                extra.unlink();profile.write_text('unrelated global profile change')
                with self.assertRaisesRegex(ValueError,'Original/global'):c.verify_runtime(root,oracle=pin)
    def test_never_imports_after_art(self):
        source=Path(c.__file__).read_text()
        self.assertNotIn('import rpg_identity_contract',source)
        self.assertNotIn('shop_personality_test_fixture',source)

if __name__=='__main__':unittest.main(verbosity=2)
