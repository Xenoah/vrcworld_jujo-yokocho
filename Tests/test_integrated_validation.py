"""Reject stale or non-rendered preview evidence. No Unity claims."""
from pathlib import Path
import hashlib, importlib.util, json, tempfile, unittest
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('integrated_validation', ROOT/'Tools/verify_integrated_source.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

class EntryProofTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name); (self.root/'Docs').mkdir()
  image=self.root/'Preview/IntegratedEntry/integrated-entry-oblique.png'
  image.parent.mkdir(parents=True); Image.new('RGB',(1440,960)).save(image)
  eye=image.with_name('integrated-entry-eye.png'); Image.new('RGB',(1440,960)).save(eye)
  self.views=[dict(file=image.name),dict(file=eye.name)]
  self.expected=dict(status='SOURCE_INPUTS_AUTHENTICATED',sourceHashes={'Source/input':'hash'},
   planAdmission='ADMITTED',unityRuntimeVerified=False,unityShaderEquivalent=False,
   historicalImagesAndProvenanceModified=False,blenderRendered=False,
   triangleCounts={'core':29032,'entry':2664,'staticControls':12},replacedExcerptMaterials=['A'])
  self.proof=dict(self.expected,blenderRendered=True,views=self.views,resolution=[1440,960],meshAttributeReadback=dict(uvCorners=95124,colorCorners=87096,maxUvDelta=0.0,maxColorDelta=0.0),imageHashes={p.relative_to(self.root).as_posix():v.sha(p) for p in (image,eye)})
 def verify(self):
  (self.root/'Docs/integrated-entry-preview-provenance.json').write_text(json.dumps(self.proof))
  return v.validate_entry_proof(self.root,self.expected,self.views)
 def test_current_render(self):self.assertEqual(self.verify()['imageCount'],2)
 def test_not_rendered(self):
  self.proof['blenderRendered']=False
  with self.assertRaisesRegex(ValueError,'rendered/admitted'):self.verify()
 def test_unadmitted(self):
  self.proof['planAdmission']='SOURCE_PREVIEW_ONLY_NOT_INSTALLER_ADMITTED'
  with self.assertRaisesRegex(ValueError,'rendered/admitted'):self.verify()
 def test_no_unity_equivalence(self):
  self.proof['unityShaderEquivalent']=True
  with self.assertRaisesRegex(ValueError,'non-Unity'):self.verify()
 def test_changed_source(self):
  self.proof['sourceHashes']={'Source/input':'old hash'}
  with self.assertRaisesRegex(ValueError,'sourceHashes'):self.verify()
 def test_changed_geometry(self):
  self.proof['triangleCounts']={'core':0}
  with self.assertRaisesRegex(ValueError,'triangleCounts'):self.verify()
 def test_empty_images(self):
  self.proof['imageHashes']={}
  with self.assertRaisesRegex(ValueError,'required image'):self.verify()
 def test_changed_image(self):
  (self.root/'Preview/IntegratedEntry/integrated-entry-oblique.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'image differs'):self.verify()
 def test_path_escape(self):
  self.proof['imageHashes']['Preview/IntegratedEntry/../../../outside.png']='hash'
  with self.assertRaisesRegex(ValueError,'required image'):self.verify()
 def test_camera_metadata_changed(self):
  self.proof['views']=[dict(file='other.png')]
  with self.assertRaisesRegex(ValueError,'camera/resolution'):self.verify()
 def test_png_dimensions_changed(self):
  image=self.root/'Preview/IntegratedEntry/integrated-entry-eye.png'
  Image.new('RGB',(1,1)).save(image); self.proof['imageHashes'][image.relative_to(self.root).as_posix()]=v.sha(image)
  with self.assertRaisesRegex(ValueError,'PNG dimensions'):self.verify()
 def test_uv_color_attribute_corruption(self):
  self.proof['meshAttributeReadback']['maxColorDelta']=0.1
  with self.assertRaisesRegex(ValueError,'readback differs'):self.verify()

class LocalPathTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);(self.root/'inside').mkdir();(self.root/'inside/file').write_text('safe')
 def test_local_file(self):self.assertEqual(v.local_path(self.root,'inside/file'),self.root/'inside/file')
 def test_absolute_path(self):
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):v.local_path(self.root,str(self.root/'inside/file'))
 def test_parent_traversal(self):
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):v.local_path(self.root,'inside/../inside/file')
 def test_file_symlink(self):
  (self.root/'link').symlink_to(self.root/'inside/file')
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):v.local_path(self.root,'link')
 def test_parent_symlink(self):
  (self.root/'alias').symlink_to(self.root/'inside',target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):v.local_path(self.root,'alias/file')
 def test_root_symlink(self):
  (self.root/'alias').symlink_to(self.root/'inside',target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'Unsafe package root'):v.local_path(self.root/'alias','file')
 def test_windows_absolute_path(self):
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):v.local_path(self.root,'C:/outside/file')

class PbrProofTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.records={}
  def write(name,data):
   path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))
   record=self.records.setdefault(name,{})
   record.update(path=name,sha256=v.sha(path),bytes=path.stat().st_size);return record
  self.write=write
  source=write('Source/author.py',{'original':True});origin=write('Docs/origin.json',{'origin':True})
  self.origin=origin['sha256'];mapping=write('Docs/mapping.json',{})
  maps=[write(f'Assets/map{i}.png',{'map':i}) for i in range(16)]
  contacts=[write(f'Preview/family{i}_contact.png',{'contact':i}) for i in range(4)]
  proofs=[write(f'Preview/review{i}.png',{'render':i}) for i in range(28)]
  self.repro=dict(status='PASS',originSha256=self.origin,checkCount=22,mapsReproduced=16,
   checks=[dict(path=r['path'],original=r['sha256'],reproduced=r['sha256'],equal=True) for r in [source,origin,*maps,*contacts]])
  repro=write('Docs/procedural_reproducibility.json',self.repro)
  bindings=[];sidecars=[]
  # Match all three production sidecar shapes: list maps, absolute-key maps,
  # and world material/slot overrides. Absolute authoring files do not exist.
  for n in range(11):
   name=f'Preview/proof{n}_authored.json'
   if n<6:
    refs=[dict(path=r['path'],sha256=r['sha256'],channel='test') for r in maps[:4]]
    pairs=[(r['path'],r) for r in refs]
   else:
    refs={'/nonexistent-authoring-root/'+r['path']:dict(sha256=r['sha256'],channel='test') for r in maps[:12]}
    pairs=list(refs.items())
   sidecars.append(write(name,dict(mode='authored',originSha256=self.origin,maps=refs)))
   bindings.extend(dict(proof=name,path=p,sha256=r['sha256'],current=True) for p,r in pairs)
  world_name='Preview/world_authored/texture_override_evidence.json'
  overrides=[[f'Material{n}',slot,maps[(n*4+k)%16]['path'],maps[(n*4+k)%16]['sha256']]
             for n in range(21) for k,slot in enumerate(('albedo','normal','roughness','ao'))]
  sidecars.append(write(world_name,dict(originSha256=self.origin,overrides=overrides)))
  bindings.extend(dict(proof=world_name,material=m,slot=s,path=p,sha256=h,current=True) for m,s,p,h in overrides)
  self.integrity=dict(status='PASS',originSha256=self.origin,requiredPairedRenders=28,currentMapBindings=168,
   bindings=bindings,proofs=proofs+contacts+sidecars)
  integrity=write('Docs/proof_integrity.json',self.integrity)
  self.roster=dict(source=source,origin=origin,mapping=mapping,maps=maps,validation=[repro,integrity],
   sourceFiles=[source],previewFiles=self.integrity['proofs'],supportingDocuments=[],historicalRenderSources=[])
  roster=write('Docs/texture_candidate_manifest.json',self.roster)
  self.review=dict(candidateManifestSha256=roster['sha256'],proofIntegritySha256=integrity['sha256'],reviewedImages=proofs)
 def reseal(self):
  # Deliberately regenerate aggregate hashes, so negative tests exercise semantic
  # gates rather than merely detecting an outdated report hash.
  self.write('Docs/procedural_reproducibility.json',self.repro)
  integrity=self.write('Docs/proof_integrity.json',self.integrity)
  roster=self.write('Docs/texture_candidate_manifest.json',self.roster)
  self.review.update(candidateManifestSha256=roster['sha256'],proofIntegritySha256=integrity['sha256'])
 def verify(self):return v.validate_pbr_roster(self.root,self.origin,self.review)
 def test_complete_current_roster(self):self.assertEqual(self.verify()['pairedImages'],28)
 def test_absolute_authoring_bindings_without_external_files(self):
  self.assertEqual(sum(Path(b['path']).is_absolute() for b in self.integrity['bindings']),60)
  self.assertEqual(self.verify()['currentMapBindings'],168)
 def test_wrong_art_identity(self):
  self.review['candidateManifestSha256']='wrong'
  with self.assertRaisesRegex(ValueError,'roster identity'):self.verify()
 def test_changed_map_bytes(self):
  (self.root/'Assets/map0.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'roster file'):self.verify()
 def test_changed_render_bytes(self):
  (self.root/'Preview/review0.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'roster file'):self.verify()
 def test_partial_visual_review(self):
  self.review['reviewedImages']=self.review['reviewedImages'][:1]
  with self.assertRaisesRegex(ValueError,'28 current'):self.verify()
 def test_duplicate_reproduction_checks(self):
  self.repro['checks']=[self.repro['checks'][0]]*22;self.reseal()
  with self.assertRaisesRegex(ValueError,'reproduction path set'):self.verify()
 def test_unexpected_reproduction_file(self):
  self.repro['checks'][-1]['path']='Preview/review0.png';self.reseal()
  with self.assertRaisesRegex(ValueError,'reproduction path set'):self.verify()
 def test_absolute_reproduction_path(self):
  self.repro['checks'][0]['path']=str(self.root/'Source/author.py');self.reseal()
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):self.verify()
 def test_traversing_reproduction_path(self):
  self.repro['checks'][0]['path']='Source/../Source/author.py';self.reseal()
  with self.assertRaisesRegex(ValueError,'Unsafe package-local path'):self.verify()
 def test_duplicate_bindings(self):
  self.integrity['bindings']=[self.integrity['bindings'][0]]*168;self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar binding multiset'):self.verify()
 def test_binding_wrong_proof(self):
  self.integrity['bindings'][0]['proof']='Preview/proof1_authored.json';self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar binding multiset'):self.verify()
 def test_binding_wrong_material(self):
  self.integrity['bindings'][-1]['material']='WrongMaterial';self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar binding multiset'):self.verify()
 def test_binding_wrong_slot(self):
  self.integrity['bindings'][-1]['slot']='WrongSlot';self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar binding multiset'):self.verify()
 def test_stale_sidecar_origin(self):
  path='Preview/proof0_authored.json';data=json.loads((self.root/path).read_text())
  data['originSha256']='old';self.write(path,data);self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar origin'):self.verify()
 def test_sidecar_binding_changed(self):
  path='Preview/proof0_authored.json';data=json.loads((self.root/path).read_text())
  data['maps'][0]['sha256']='old';self.write(path,data);self.reseal()
  with self.assertRaisesRegex(ValueError,'sidecar binding multiset'):self.verify()
 def test_absolute_binding_wrong_suffix(self):
  self.integrity['bindings'][24]['path']='/old-root/NotAssets/map0.png';self.reseal()
  with self.assertRaisesRegex(ValueError,'material binding'):self.verify()
if __name__=='__main__':unittest.main()
