"""Regenerate in a throwaway output, compare exact authored input bytes; never alter pins."""
from pathlib import Path
import sys,tempfile,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parent.parent;BASE=Path(sys.argv[1]).resolve();asset=Path('Assets/TreeTopYokochoEntrySystems/EntryPlaza')
with tempfile.TemporaryDirectory(prefix='yokocho-entry-reproduction-') as tmp:
 subprocess.run([sys.executable,str(ROOT/'Source/build_entry_plaza.py'),str(BASE),tmp],check=True)
 results=[]
 for source in sorted((ROOT/asset).rglob('*')):
  if not source.is_file() or source.suffix=='.meta':continue
  relative=source.relative_to(ROOT/asset);generated=Path(tmp)/asset/relative;sha=hashlib.sha256(source.read_bytes()).hexdigest()
  results.append(dict(path=str(relative),sha256=sha,reproduced=generated.exists() and hashlib.sha256(generated.read_bytes()).hexdigest()==sha))
 report=dict(status='PASS' if all(x['reproduced'] for x in results) else 'FAIL',scope='Native meshes, declarative JSON and all baked textures reproduce byte-for-byte from authored source and immutable v2.19 input.',files=results)
 (ROOT/'Docs/entry-source-reproduction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert all(x['reproduced'] for x in results)
