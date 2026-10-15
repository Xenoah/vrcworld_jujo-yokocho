"""Write missing Unity metadata only for the additive integration/PBR roots.
Existing metadata is never replaced. Import policy is enforced in C# as well.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OWNED = ('Assets/TreeTopYokochoIntegration', 'Assets/TreeTopYokochoOriginalPbr')

def metadata(path):
    rel = path.relative_to(ROOT).as_posix()
    guid = hashlib.sha256(('TreeTopYokocho/IntegratedPreview/v1/' + rel).encode()).hexdigest()[:32]
    text = f'fileFormatVersion: 2\nguid: {guid}\n'
    if path.is_dir():
        text += 'folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n'
    elif path.suffix == '.cs':
        text += 'MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n'
    elif path.suffix == '.png':
        normal = path.name.endswith('_normalGL.png')
        albedo = path.name.endswith('_albedo.png')
        cap = 2048 if albedo and not path.name.startswith('yokocho_mineral_rock_') else 1024
        text += f'''TextureImporter:
  externalObjects: {{}}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: {int(albedo)}
    linearTexture: 0
  isReadable: 0
  textureType: {1 if normal else 0}
  textureShape: 1
  maxTextureSize: {cap}
  textureSettings:
    serializedVersion: 2
    filterMode: 2
    aniso: 4
    mipBias: 0
    wrapU: 0
    wrapV: 0
    wrapW: 0
'''
    else:
        importer = 'TextScriptImporter' if path.suffix in ('.json', '.txt', '.md', '.bytes') else 'DefaultImporter'
        text += importer + ':\n  externalObjects: {}\n'
    return text + '  userData: \n  assetBundleName: \n  assetBundleVariant: \n'

if __name__ == '__main__':
    written = []
    for relative in OWNED:
        folder = ROOT / relative
        if not folder.is_dir():
            continue
        for path in [folder, *sorted(folder.rglob('*'))]:
            if path.name.endswith('.meta') or 'Generated' in path.parts:
                continue
            target = Path(str(path) + '.meta')
            if not target.exists():
                target.write_text(metadata(path))
                written.append(target.relative_to(ROOT).as_posix())
    print('\n'.join(written))
