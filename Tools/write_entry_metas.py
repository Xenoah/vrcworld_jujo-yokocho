"""Add deterministic missing metadata only; never replace supplied GUIDs."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]/'Assets'
for p in sorted(ROOT.rglob('*')):
 if p.name.endswith('.meta'):continue
 meta=Path(str(p)+'.meta')
 if meta.exists():continue
 guid=hashlib.sha256(('TreeTopYokochoEntrySystems/v1/'+str(p.relative_to(ROOT))).encode()).hexdigest()[:32]
 text=f'fileFormatVersion: 2\nguid: {guid}\n'
 if p.is_dir():text+='folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n'
 else:
  importer='TextScriptImporter' if p.suffix in ['.txt','.json','.md','.bytes'] else 'DefaultImporter'
  text+=importer+':\n  externalObjects: {}\n'
 text+='  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
 meta.write_text(text)
