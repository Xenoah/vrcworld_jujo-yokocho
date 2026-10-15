"""Stable addon-local Unity metadata. Never scans or writes core asset paths."""
from pathlib import Path
import uuid
ROOT=Path(__file__).resolve().parent.parent
asset=ROOT/'Assets/TreeTopYokochoEntrySystems/EntryPlaza'
files=[asset]+sorted(p for p in asset.rglob('*') if p.suffix!='.meta')+[ROOT/'Assets/TreeTopYokochoEntrySystems/Editor/EntryPlazaBuilder.cs']
for p in files:
 relative=p.relative_to(ROOT).as_posix();guid=uuid.uuid5(uuid.NAMESPACE_URL,'yokocho-entry-plaza-v1/'+relative).hex
 text='fileFormatVersion: 2\nguid: '+guid+'\n'
 if p.is_dir():text+='folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
 elif p.suffix=='.cs':text+='MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
 elif p.suffix=='.png':
  wrap=0 if p.stem in ['EntryTimber','EntryEndgrain'] else 1
  text+='''TextureImporter:
  externalObjects: {}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: 1
  isReadable: 0
  streamingMipmaps: 0
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 4
    mipBias: 0
    wrapU: WRAP
    wrapV: WRAP
    wrapW: WRAP
  textureType: 0
  textureShape: 1
  alphaSource: 0
  alphaIsTransparency: 0
  textureCompression: 0
  userData: Source-authored entry furniture and Japanese baked print. No added runtime lights.
  assetBundleName: 
  assetBundleVariant: 
'''.replace('WRAP',str(wrap))
 else:text+='DefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
 Path(str(p)+'.meta').write_text(text)
