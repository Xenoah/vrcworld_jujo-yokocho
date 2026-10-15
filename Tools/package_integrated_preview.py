"""Package the additive integrated source preview without changing the v2.19 core.
Does not publish or claim Unity/Udon/VRChat validation.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, tempfile, zipfile
VERSION='2.20.0-preview.1'
DIRS=('Assets','Docs','Packages','ProjectSettings','Source','Tests','Tools','Preview')
SKIP={'__pycache__','Generated','.git','.venv','Baseline'}
SKIP_SUFFIXES=('.pyc','.blend','.exr','.tmp.glb')

def sha(data):return hashlib.sha256(data).hexdigest()
def inventory(root):
 root=Path(root);found={}
 for folder in DIRS:
  for p in (root/folder).rglob('*'):
   rel=p.relative_to(root)
   if not p.is_file() or any(x in SKIP for x in rel.parts) or p.name == 'Generated.meta' or p.name.endswith(SKIP_SUFFIXES):continue
   # Include the paired original-PBR raw world proofs, not the large legacy
   # preview working directories. Both raw and denoised evidence stay available.
   if 'Raw' in rel.parts and rel.parts[:3] not in (('Preview','world_authored','Raw'),('Preview','world_baseline','Raw')):continue
   if any(x.is_symlink() for x in (p,*p.parents) if x != root and x.is_relative_to(root)):raise ValueError('No symlinks in source package: '+str(rel))
   if rel.parent==Path('Assets/TreeTopYokocho/Data') and (p.suffix=='.bytes' or p.name.endswith('.bytes.meta') or p.name in ('VisualMeshes.bytes.gz','VisualMeshes.bytes.gz.meta')):continue
   if rel.suffix=='.html':continue
   found[rel.as_posix()]=p
 for name in ('README.md','README_JA.md','.gitignore','.gitattributes','PACKAGE_MANIFEST.json'):
  if (root/name).is_file():found[name]=root/name
 for name,p in found.items():
  if any(x.is_symlink() for x in (p,*p.parents) if x != root and x.is_relative_to(root)):raise ValueError('No symlinks in source package: '+name)
 return dict(sorted(found.items()))

def package(root,output):
 root=Path(root).resolve();output=Path(output).resolve()
 if output.is_relative_to(root):raise ValueError('Archive must be outside source root')
 paths=inventory(root)
 required=('Source/TreeTopYokocho.glb','Source/run_checks.py','Tools/run_integrated_checks.py','Assets/TreeTopYokocho/Data/GeometryShards.json',
  'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes.gz','Assets/TreeTopYokocho/Data/WorldManifest.json',
  'Assets/TreeTopYokochoOriginalPbr/Data/OriginalPbrPlan.json','Docs/ORIGINAL_PBR_REVIEW.json','Docs/integrated-source-validation.json')
 if any(p not in paths for p in required):raise ValueError('Missing required source/review: '+str([p for p in required if p not in paths]))
 plan_path=root/'Assets/TreeTopYokochoOriginalPbr/Data/OriginalPbrPlan.json';plan=json.loads(plan_path.read_text())
 frozen=re.search(r'ApprovedPlanSha256 = "([0-9a-f]{64})";', (root/'Assets/TreeTopYokochoIntegration/Editor/OriginalPbrInstaller.cs').read_text())
 if frozen is None or frozen[1]!=sha(plan_path.read_bytes()):raise ValueError('PBR art/source admission not frozen or differs')
 if len(plan['maps'])!=16 or any(x['path'] not in paths or sha(paths[x['path']].read_bytes())!=x['sha256'] for x in plan['maps']):raise ValueError('Missing/changed authored maps')
 review=json.loads((root/'Docs/ORIGINAL_PBR_REVIEW.json').read_text());validation=json.loads((root/'Docs/integrated-source-validation.json').read_text())
 if review['sourcePreviewAccepted'] is not True or review['unityRuntimeVerified'] is not False or validation['status']!='PASS':raise ValueError('Missing source preview admission')
 verified=validation.get('verifiedInventory',{})
 if not verified or set(verified)!=set(paths)-{'Docs/integrated-source-validation.json'} or any(sha(paths[p].read_bytes())!=h for p,h in verified.items()):raise ValueError('Source changed since integrated verification (complete inventory)')
 identity={'packageVersion':VERSION,'coreVersion':'2.19.0','entrySystemsVersion':'0.1.0','publicationStatus':'SOURCE_PREVIEW','compiledWorld':False,
  'unityRuntimeVerified':False,'vrchatRuntimeVerified':False,'sourceBaseCommit':'97091c96cf66a0f67b952827a753a448768f175a',
  'primaryUnityMenu':'Tools/TreeTop Yokocho/0 - Build or Complete Preview','files':{name:sha(p.read_bytes()) for name,p in paths.items()}}
 data=(json.dumps(identity,ensure_ascii=False,indent=2)+'\n').encode();(root/'ARCHIVE_IDENTITY.json').write_bytes(data)
 output.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix=output.name+'.',suffix='.tmp',dir=output.parent);os.close(fd)
 try:
  with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for name,p in paths.items():
    entry=zipfile.ZipInfo('TreeTopYokocho/'+name,(2026,10,15,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16
    z.writestr(entry,p.read_bytes())
   entry=zipfile.ZipInfo('TreeTopYokocho/ARCHIVE_IDENTITY.json',(2026,10,15,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16;z.writestr(entry,data)
  with zipfile.ZipFile(tmp) as z:
   if z.testzip():raise ValueError('CRC failure')
   if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate archive names')
   for name,digest in identity['files'].items():
    if sha(z.read('TreeTopYokocho/'+name))!=digest or sha(paths[name].read_bytes())!=digest:raise ValueError('Source changed or archive differs: '+name)
  os.replace(tmp,output)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 return {'packageVersion':VERSION,'archive':str(output),'bytes':output.stat().st_size,'sha256':sha(output.read_bytes()),'files':len(paths)+1,'crcPass':True,'everyFileHashMatches':True,'unityTested':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(package(a.root,a.output),indent=2))
