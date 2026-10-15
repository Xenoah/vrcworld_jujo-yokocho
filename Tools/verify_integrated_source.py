"""Verify current integrated-package bytes, not a Unity or VRChat execution.

The historical baseline identity is authenticated independently; existing core
implementation/oracles cannot be silently relabelled as a new implementation.
"""
from pathlib import Path, PureWindowsPath
from collections import Counter
import argparse, hashlib, importlib.util, json, re

BASELINE_IDENTITY = 'Docs/History/ARCHIVE_IDENTITY_v2.19.0.json'
BASELINE_IDENTITY_SHA = 'ad19874bc39c88f465381c54b80fc17bfd41946b29a5a491ed62cf0e229d5e41'
PRESERVE_PREFIXES = ('Assets/', 'Source/', 'Tools/', 'Packages/', 'ProjectSettings/')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())

def local_path(root, name):
    """Admit an existing package-local file before any caller reads its bytes."""
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Unsafe package root symlink')
    root = root.resolve()
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('Unsafe package-local path: ' + repr(name))
    relative = Path(name)
    if (relative.is_absolute() or PureWindowsPath(name).drive or '..' in relative.parts
            or name != relative.as_posix()):
        raise ValueError('Unsafe package-local path: ' + name)
    path = root / relative
    if (any(root.joinpath(*relative.parts[:i]).is_symlink() for i in range(1, len(relative.parts) + 1))
            or not path.resolve().is_relative_to(root) or not path.is_file()):
        raise ValueError('Unsafe package-local path: ' + name)
    return path

def validate_entry_proof(root, expected, views):
    """Require a real Blender preview whose full declared inputs are still current."""
    root = Path(root).resolve()
    proof = load(root / 'Docs/integrated-entry-preview-provenance.json')
    if not (proof.get('blenderRendered') is True and proof.get('planAdmission') == 'ADMITTED'
            and proof.get('unityRuntimeVerified') is False and proof.get('unityShaderEquivalent') is False
            and proof.get('historicalImagesAndProvenanceModified') is False):
        raise ValueError('Integrated entry proof must be rendered/admitted and explicitly non-Unity')
    for name, value in expected.items():
        if name != 'blenderRendered' and proof.get(name) != value:
            raise ValueError('Integrated entry proof differs from current source: ' + name)
    if proof.get('views') != views or proof.get('resolution') != [1440, 960]:
        raise ValueError('Integrated entry proof camera/resolution differs')
    readback = proof.get('meshAttributeReadback', {})
    if not (readback.get('uvCorners') == 95124 and readback.get('colorCorners') == 87096
            and 0 <= readback.get('maxUvDelta', float('inf')) <= 1e-6
            and 0 <= readback.get('maxColorDelta', float('inf')) <= 1e-6):
        raise ValueError('Integrated entry mesh UV/color readback differs')
    images = proof.get('imageHashes', {})
    if set(images) != {'Preview/IntegratedEntry/' + view['file'] for view in views}:
        raise ValueError('Integrated entry proof has no required image')
    for name, digest in images.items():
        path = root / name
        if (not name.startswith('Preview/IntegratedEntry/') or Path(name).suffix != '.png'
                or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(root)
                or not path.is_file() or sha(path) != digest):
            raise ValueError('Integrated entry proof image differs: ' + name)
        from PIL import Image
        with Image.open(path) as bitmap:
            if bitmap.format != 'PNG' or bitmap.size != (1440, 960):
                raise ValueError('Integrated entry proof PNG dimensions differ: ' + name)
            bitmap.verify()
    return dict(sourceCount=len(proof['sourceHashes']), imageCount=len(images),
                triangleCounts=proof['triangleCounts'], replacedMaterials=len(proof['replacedExcerptMaterials']))

def validate_pbr_roster(root, origin_sha, review):
    roster_path = local_path(root, 'Docs/texture_candidate_manifest.json')
    integrity_path = local_path(root, 'Docs/proof_integrity.json')
    root = Path(root).resolve()
    if review.get('candidateManifestSha256') != sha(roster_path) or review.get('proofIntegritySha256') != sha(integrity_path):
        raise ValueError('PBR art review roster identity differs')
    roster = load(roster_path); integrity = load(integrity_path)
    records = [roster['source'], roster['origin'], roster['mapping']]
    for group in ('maps', 'validation', 'sourceFiles', 'previewFiles', 'supportingDocuments', 'historicalRenderSources'):
        records.extend(roster[group])
    for item in records:
        name = item['path']; path = local_path(root, name)
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError('PBR roster file differs: ' + name)
    if not (roster['origin']['sha256'] == origin_sha == integrity['originSha256']
            and integrity['status'] == 'PASS' and integrity['requiredPairedRenders'] == 28
            and integrity['proofs'] == roster['previewFiles']):
        raise ValueError('PBR proof integrity identity/paired roster differs')
    current_maps = {r['path']: r['sha256'] for r in roster['maps']}
    if len(current_maps) != len(roster['maps']) or len(current_maps) != 16:
        raise ValueError('PBR roster must contain sixteen unique maps')
    bindings = integrity['bindings']
    def binding_matches(binding):
        # Some original render sidecars retain the absolute authoring-root path.
        # Authenticate its complete package-relative suffix and digest, without
        # rewriting the historical sidecar or reading outside this package.
        path = binding['path']
        matches = [p for p in current_maps if path == p or (Path(path).is_absolute() and path.endswith('/' + p))]
        return (binding['current'] is True and '..' not in Path(path).parts and len(matches) == 1
                and current_maps[matches[0]] == binding['sha256'])
    if not (len(bindings) == integrity['currentMapBindings'] == 168
            and all(binding_matches(b) for b in bindings)):
        raise ValueError('PBR proof material binding differs')

    # Reconstruct the report from authenticated original sidecars. A correct map
    # repeated 168 times is not evidence for the original proof/material/slots.
    extracted = []
    sidecar_count = 0
    for item in roster['previewFiles']:
        name = item['path']
        if not name.endswith('.json'):
            continue
        sidecar = load(local_path(root, name))
        is_maps = sidecar.get('mode') == 'authored' and 'maps' in sidecar
        is_world = name == 'Preview/world_authored/texture_override_evidence.json'
        if not (is_maps or is_world):
            continue
        if sidecar.get('originSha256') != origin_sha:
            raise ValueError('PBR proof sidecar origin differs: ' + name)
        sidecar_count += 1
        if is_maps:
            maps = sidecar['maps']
            pairs = maps.items() if isinstance(maps, dict) else ((m['path'], m) for m in maps)
            extracted.extend(dict(proof=name, path=p, sha256=m['sha256'], current=True) for p, m in pairs)
        else:
            extracted.extend(dict(proof=name, material=m, slot=s, path=p, sha256=h, current=True)
                             for m, s, p, h in sidecar['overrides'])
    canonical = lambda record: json.dumps(record, sort_keys=True, separators=(',', ':'))
    if (sidecar_count != 12 or Counter(map(canonical, extracted)) != Counter(map(canonical, bindings))):
        raise ValueError('PBR proof sidecar binding multiset differs')

    repro = load(local_path(root, 'Docs/procedural_reproducibility.json'))
    contacts = {r['path'] for r in roster['previewFiles'] if r['path'].endswith('_contact.png')}
    expected_repro = {roster['source']['path'], roster['origin']['path']} | set(current_maps) | contacts
    # Validate every path before hashing any check, including a bad extra check.
    check_paths = [local_path(root, c['path']) for c in repro['checks']]
    if (len(contacts) != 4 or len(expected_repro) != 22 or len(repro['checks']) != 22
            or {c['path'] for c in repro['checks']} != expected_repro):
        raise ValueError('PBR independent reproduction path set differs')
    if not (repro['status'] == 'PASS' and repro['originSha256'] == origin_sha
            and repro['checkCount'] == len(repro['checks']) == 22 and repro['mapsReproduced'] == 16
            and all(c['equal'] is True and c['original'] == c['reproduced'] == sha(p)
                    for c, p in zip(repro['checks'], check_paths))):
        raise ValueError('PBR independent reproduction no longer matches delivered bytes')
    reviewed = review['reviewedImages']
    png_roster = {r['path']: r['sha256'] for r in roster['previewFiles'] if r['path'].endswith('.png')}
    if len(reviewed) != 28 or len({r['path'] for r in reviewed}) != 28 or any(png_roster.get(r['path']) != r['sha256'] for r in reviewed):
        raise ValueError('PBR art review must cover 28 current paired images')
    return dict(rosterRecords=len(records), uniqueFiles=len({r['path'] for r in records}), pairedImages=len(reviewed), currentMapBindings=len(bindings), reproductionFiles=22)

def verify(root):
    root = Path(root).resolve()
    checks = []
    def require(value, label, detail=None):
        checks.append(dict(check=label, passed=bool(value), detail=detail))
        if not value: raise ValueError(label + ': ' + str(detail))
    require(sha(root / BASELINE_IDENTITY) == BASELINE_IDENTITY_SHA, 'historical identity authenticated')
    identity = load(root / BASELINE_IDENTITY)
    preserved = {p: h for p, h in identity['files'].items() if p.startswith(PRESERVE_PREFIXES)}
    # The derived GLB is release-only, not tracked in Git. Its exact reproduction
    # is required here after the unchanged core suite has constructed it.
    changed = [p for p, h in preserved.items() if not (root / p).is_file() or sha(root / p) != h]
    require(not changed, 'all pre-existing core source/assets/oracles preserved', dict(count=len(preserved), changed=changed))
    spec = importlib.util.spec_from_file_location('plan_builder', root / 'Tools/build_original_pbr_plan.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    plan_path = root / 'Assets/TreeTopYokochoOriginalPbr/Data/OriginalPbrPlan.json'
    plan = load(plan_path)
    require(plan_path.read_bytes() == builder.encode(builder.build(root)), 'current material plan exactly reproducible')
    installer = (root / 'Assets/TreeTopYokochoIntegration/Editor/OriginalPbrInstaller.cs').read_text()
    frozen = re.search(r'ApprovedPlanSha256 = "([0-9a-f]{64})";', installer)
    require(frozen is not None and frozen[1] == sha(plan_path), 'reviewed plan hash admitted by installer')
    require(len(plan['materials']) == 31 and sum(r['expectedRendererCount'] > 0 for r in plan['materials']) == 30,
            '31 definitions / 30 active replacements')
    require(sum(r['expectedRendererCount'] for r in plan['materials']) == 523
            and sum(len(r['slots']) for r in plan['materials']) == 88, '523 renderer references / 88 material texture slots')
    require(sum(r['calibrateParallax'] for r in plan['materials']) == 10, 'only ten existing nonzero parallax fields calibrated')
    origin = load(root / 'Docs/authored_pbr_origin.json')
    require(origin['externalInputs'] == [] and origin['downloads'] == [] and origin['imageModelUsed'] is False,
            'procedural original provenance has no external image inputs')
    require(sha(root / origin['sourcePath']) == origin['sourceSha256'], 'original generator identity')
    maps = {m['path']: m['sha256'] for f in origin['families'] for m in f['maps'].values()}
    require(len(maps) == 16 and maps == {x['path']: x['sha256'] for x in plan['maps']}, 'plan/provenance map identities agree')
    require(all(sha(root / p) == h for p, h in maps.items()), 'all sixteen installed map bytes match provenance')
    validation = load(root / 'Docs/authored_pbr_validation.json')
    seams = load(root / 'Docs/multiscale_seam_validation.json')
    require(validation['passed'] and validation['count'] == 92 and not validation['failed']
            and validation['originSha256'] == sha(root / 'Docs/authored_pbr_origin.json'), '92 encoded map/coherence checks')
    require(seams['status'] == 'PASS' and len(seams['checks']) == 80 and not seams['failed']
            and seams['originSha256'] == sha(root / 'Docs/authored_pbr_origin.json'), '80 multiscale wrap/derivative checks')
    review = load(root / 'Docs/ORIGINAL_PBR_REVIEW.json')
    require(review['sourcePreviewAccepted'] is True and review['unityRuntimeVerified'] is False
            and review['originSha256'] == sha(root / 'Docs/authored_pbr_origin.json'), 'explicit source-preview art review tied to current maps')
    require(review.get('generatorSha256') == sha(root / origin['sourcePath']) and review.get('planSha256') == sha(plan_path), 'art review admits the exact current generator and material plan')
    require(bool(review['reviewedImages']) and all(sha(local_path(root, r['path'])) == r['sha256'] for r in review['reviewedImages']), 'reviewed images are current delivered bytes')
    require(True, 'PBR render roster and independent reproduction are current', validate_pbr_roster(root, sha(root / 'Docs/authored_pbr_origin.json'), review))
    entry_spec = importlib.util.spec_from_file_location('integrated_entry_proof', root / 'Source/render_integrated_entry_preview.py')
    entry = importlib.util.module_from_spec(entry_spec); entry_spec.loader.exec_module(entry)
    entry_current = entry.prepare(root, True)[0]
    require(True, 'integrated entry Blender proof bound to current admitted inputs', validate_entry_proof(root, entry_current, entry.VIEWS))
    guids = {}; missing = []; malformed = []; orphaned = []
    for asset in (root / 'Assets').rglob('*'):
        if 'Generated' in asset.parts: continue
        if asset.name.endswith('.meta'):
            if not Path(str(asset)[:-5]).exists(): orphaned.append(asset.relative_to(root).as_posix())
            found = re.search(r'^guid: ([0-9a-f]{32})$', asset.read_text(), re.M)
            if not found: malformed.append(asset.relative_to(root).as_posix())
            else: guids.setdefault(found[1], []).append(asset.relative_to(root).as_posix())
        elif not Path(str(asset) + '.meta').is_file():
            # Raw bytes reconstructed by offline core tests are intentionally
            # ignored; the authenticated gzip/shards remain Unity source input.
            if asset.parent == root / 'Assets/TreeTopYokocho/Data' and asset.suffix == '.bytes': continue
            missing.append(asset.relative_to(root).as_posix())
    duplicates = {g: p for g, p in guids.items() if len(p) != 1}
    require(not missing and not malformed and not orphaned and not duplicates, 'complete unique Unity metadata',
            dict(missing=missing, malformed=malformed, orphaned=orphaned, duplicates=duplicates, guidCount=len(guids)))
    mp3 = [p for p in (root / 'Assets').rglob('*') if p.is_file() and p.suffix.lower() == '.mp3']
    require(not mp3, 'no unlicensed MP3 silently bundled', dict(bundledMp3Count=len(mp3)))
    package = load(root / 'PACKAGE_MANIFEST.json')
    require(package['version'] == '2.20.0-preview.1' and package['unityRuntimeVerified'] is False
            and package['vrchatRuntimeVerified'] is False, 'package labelled source preview only')
    source_paths = [p for folder in ('Assets', 'Source', 'Tools', 'Tests') for p in (root / folder).rglob('*')
                    if p.is_file() and p.suffix in ('.cs', '.shader', '.py', '.json') and 'Generated' not in p.parts and '__pycache__' not in p.parts]
    source_paths += [root / p for p in ('README.md', 'PACKAGE_MANIFEST.json', 'Docs/REQUIREMENTS_STATUS_JA.md',
                     'Docs/MCP_UNITY_SETUP_JA.md', 'Docs/MCP_UNITY_VERIFICATION_TEMPLATE_JA.md', 'Docs/ORIGINAL_PBR_REVIEW.json')]
    source_hashes = {p.relative_to(root).as_posix(): sha(p) for p in sorted(source_paths)}
    packaging_spec = importlib.util.spec_from_file_location('integrated_packaging', root / 'Tools/package_integrated_preview.py')
    packaging = importlib.util.module_from_spec(packaging_spec); packaging_spec.loader.exec_module(packaging)
    verified_inventory = {name: sha(path) for name, path in packaging.inventory(root).items()
                          if name != 'Docs/integrated-source-validation.json'}
    result = dict(status='PASS', scope='Offline current-source contracts, not Unity/Udon/VRChat execution',
                  unityExecuted=False, vrchatExecuted=False, checkCount=len(checks), checks=checks,
                  sourceHashes=source_hashes, verifiedInventory=verified_inventory)
    (root / 'Docs/integrated-source-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('root', type=Path)
    args = parser.parse_args(); print(json.dumps(verify(args.root), indent=2))
