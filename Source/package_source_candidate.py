"""Package current source bytes, never publication snapshots. Offline only.
The output is an unpublished source candidate, not a compiled VRChat world.
"""
import argparse, hashlib, json, os, tempfile, zipfile
from pathlib import Path

ROOT_DIRS = ('Assets', 'Docs', 'Packages', 'ProjectSettings', 'Source', 'Tests', 'Tools')
SKIP_DIRS = {'__pycache__', 'Generated', '.venv', '.git'}
SKIP_SUFFIXES = ('.pyc', '.blend', '.exr', '.tmp.glb')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inventory(root, previews):
    paths = [root / 'README.md']
    for name in ROOT_DIRS:
        paths.extend(p for p in (root / name).rglob('*') if p.is_file())
    # Keep documented historical previews; raw guides/HTML are opt-in, not
    # accidentally bundled. Each preview's sidecar records its own version.
    paths.extend(p for p in (root / 'Preview').glob('*') if p.is_file() and p.suffix in ('.png', '.json'))
    for name in ('.gitignore', '.gitattributes'):
        if (root / name).is_file(): paths.append(root / name)
    for preview in previews:
        path = Path(preview)
        if not path.parts or path.is_absolute() or '..' in path.parts or path.parts[0] != 'Preview':
            raise ValueError('Preview must be a relative path below Preview/')
        paths.append(root / path)
    result = {}
    for path in sorted(set(paths)):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts): continue
        if str(rel).endswith(SKIP_SUFFIXES): continue
        # The shard-only source delivery remains runnable by run_checks.py.
        if rel.parent == Path('Assets/TreeTopYokocho/Data') and (
            '.bytes' == path.suffix or path.name.endswith('.bytes.meta') or
            path.name in ('VisualMeshes.bytes.gz', 'VisualMeshes.bytes.gz.meta')):
            continue
        if any(candidate.is_symlink() for candidate in [path, *path.parents] if candidate != root and candidate.is_relative_to(root)):
            raise ValueError('Symlink not allowed: ' + str(rel))
        if not path.is_file(): raise FileNotFoundError(path)
        result[rel.as_posix()] = path
    required = ['Source/TreeTopYokocho.glb', 'Source/run_checks.py',
                'Assets/TreeTopYokocho/Data/GeometryShards.json',
                'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes.gz',
                'Assets/TreeTopYokocho/Data/WorldManifest.json']
    for name in required:
        if name not in result: raise ValueError('Missing required source: ' + name)
    return result

def package(root, output, previews, base_commit):
    root = root.resolve(); output = output.resolve()
    if output.is_relative_to(root): raise ValueError('Write archive outside source root')
    paths = inventory(root, previews)
    version = json.loads(paths['Assets/TreeTopYokocho/Data/WorldManifest.json'].read_text())['version']
    identity = {'version': version, 'publicationStatus': 'UNPUBLISHED_CANDIDATE',
        'gitCommit': None, 'publishedBaseCommit': base_commit,
        'scope': 'Current source bytes; no compiled Windows VRChat world',
        'blenderPreviewNotRuntime': True, 'actualWindowsBuildBytes': None,
        'files': {}}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output.name + '.', suffix='.tmp', dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, source in paths.items():
                data = source.read_bytes()
                identity['files'][name] = sha(data)
                entry = zipfile.ZipInfo('TreeTopYokocho/' + name, (2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data)
            entry = zipfile.ZipInfo('TreeTopYokocho/ARCHIVE_IDENTITY.json', (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, json.dumps(identity, indent=2, ensure_ascii=False) + '\n')
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None: raise ValueError('Archive CRC failure')
            if len(archive.namelist()) != len(set(archive.namelist())): raise ValueError('Duplicate entries')
            for name, digest in identity['files'].items():
                if sha(archive.read('TreeTopYokocho/' + name)) != digest:
                    raise ValueError('Archive hash mismatch: ' + name)
                if sha(paths[name].read_bytes()) != digest:
                    raise ValueError('Source changed during packaging: ' + name)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return {'status': 'PASS', 'path': str(output), 'version': version,
            'bytes': output.stat().st_size, 'sha256': sha(output.read_bytes()),
            'files': len(paths) + 1, 'publicationStatus': 'UNPUBLISHED_CANDIDATE',
            'checks': 'CRC, unique entries, each archived hash, each current source hash; extracted run_checks still required'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--preview', action='append', default=[])
    parser.add_argument('--published-base', required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.root, args.output, args.preview, args.published_base), indent=2))
