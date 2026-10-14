"""Archive plumbing regression; synthetic files, not Unity/package acceptance."""
from pathlib import Path
import json,tempfile,unittest,zipfile
from package_source_candidate import package,inventory
class CurrentSourcePackaging(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'source';self.root.mkdir()
        files={'README.md':b'current source','Source/TreeTopYokocho.glb':b'synthetic glb',
            'Source/run_checks.py':b'# synthetic runner',
            'Assets/TreeTopYokocho/Data/GeometryShards.json':b'{}',
            'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes.gz':b'gz',
            'Assets/TreeTopYokocho/Data/WorldManifest.json':b'{"version":"test"}'}
        for rel,data in files.items():p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    def tearDown(self):self.tmp.cleanup()
    def test_current_bytes_and_determinism(self):
        a=self.base/'a.zip';b=self.base/'b.zip'
        one=package(self.root,a,[],None);two=package(self.root,b,[],None)
        self.assertEqual(one['sha256'],two['sha256'])
        with zipfile.ZipFile(a) as z:
            self.assertEqual(z.read('TreeTopYokocho/README.md'),b'current source')
            identity=json.loads(z.read('TreeTopYokocho/ARCHIVE_IDENTITY.json'))
            self.assertEqual(identity['publicationStatus'],'UNPUBLISHED_CANDIDATE')
            self.assertIsNone(identity['actualWindowsBuildBytes'])
    def test_raw_geometry_and_cache_excluded(self):
        for name in ['VisualMeshes.bytes','VisualMeshes.bytes.gz','VisualMeshes.bytes.meta']:
            (self.root/'Assets/TreeTopYokocho/Data'/name).write_bytes(b'unwanted')
        cache=self.root/'Source/__pycache__';cache.mkdir();(cache/'x.pyc').write_bytes(b'cache')
        names=inventory(self.root,[])
        self.assertNotIn('Assets/TreeTopYokocho/Data/VisualMeshes.bytes',names)
        self.assertNotIn('Assets/TreeTopYokocho/Data/VisualMeshes.bytes.gz',names)
        self.assertNotIn('Source/__pycache__/x.pyc',names)
    def test_unbounded_paths_rejected(self):
        for preview in ['', '../secret.png','/tmp/image.png','Docs/not-preview.png']:
            with self.assertRaises(ValueError):inventory(self.root,[preview])
        with self.assertRaises(ValueError):package(self.root,self.root/'recursive.zip',[],None)
    def test_symlinks_rejected(self):
        (self.root/'Source/link.py').symlink_to(self.root/'README.md')
        with self.assertRaises(ValueError):inventory(self.root,[])
    def test_preview_symlink_parent_rejected(self):
        preview=self.root/'Preview';preview.mkdir()
        outside=self.root.parent/'external';outside.mkdir()
        (outside/'image.png').write_bytes(b'not inside source')
        (preview/'linked').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):inventory(self.root,['Preview/linked/image.png'])
    def test_documented_previews_but_not_large_html(self):
        preview=self.root/'Preview';preview.mkdir()
        (preview/'old.png').write_bytes(b'example')
        (preview/'old.json').write_text('{}')
        (preview/'huge.html').write_text('not included')
        names=inventory(self.root,[])
        self.assertIn('Preview/old.png',names);self.assertIn('Preview/old.json',names)
        self.assertNotIn('Preview/huge.html',names)
    def test_new_current_file_included(self):
        (self.root/'Source/new_module.py').write_text('new code')
        self.assertIn('Source/new_module.py',inventory(self.root,[]))
if __name__=='__main__':unittest.main()
