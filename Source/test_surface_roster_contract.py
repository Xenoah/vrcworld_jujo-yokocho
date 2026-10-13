"""Read-only tests for exactly eight explicitly gated roof batch identities.

The added triangles are synthetic roster fixtures, not roof/art validation.
"""
import argparse
import copy
import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np
import peer_culling_contract as c
from test_peer_culling_contract import Tests

EXPECTED_ADDITIONS = {
    ('Shops/S01/Joinery', 'RoofCopper'), ('Shops/S02/Joinery', 'RoofCopper'),
    ('Shops/S03/Joinery', 'RoofCopper'), ('Shops/S04/Joinery', 'RoofCopper'),
    ('Shops/S05/Joinery', 'RoofCopper'), ('Shops/S06/Joinery', 'RoofCopper'),
    ('Shops/S07/Joinery', 'RoofCopper'), ('Shops/S08/Joinery', 'RoofCopper'),
}
PINNED_BASELINE_SHA256 = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'


def write_visual(path, batches):
    with path.open('wb') as stream:
        stream.write(b'JYWM' + struct.pack('<II', 1, len(batches)))
        for batch in batches:
            for name in c.key(batch):
                raw = name.encode('utf-8')
                stream.write(struct.pack('<I', len(raw)) + raw)
            stream.write(struct.pack('<II', len(batch['vertices']), batch['faces'].size))
            stream.write(c.raw_attributes(batch))


def run(args, tests):
    baseline = c.load_baseline(args.root)
    peer = c.read_visual(args.fixture / 'frozen_v28_induced_split.bytes')
    peer_manifest = json.loads((args.fixture / 'frozen_v28_induced_split_manifest.json').read_text())
    peer_rows = [c.summarize(batch) for batch in peer]
    tests.expect('pinning', 'exact eight independent allowed identities', lambda:
                 set(c.SURFACE_REFINEMENT_BATCHES) == EXPECTED_ADDITIONS
                 and len(c.SURFACE_REFINEMENT_BATCHES) == 8)
    tests.expect('pinning', 'frozen baseline bytes unchanged', lambda: hashlib.sha256(
        (args.root / 'Docs/baselines' / c.BASELINE_NAME).read_bytes()).hexdigest() == PINNED_BASELINE_SHA256)
    gutters = [dict(group=group, material=material,
                    vertices=np.array([[i, 0, 0], [i+1, 0, 0], [i, 1, 0]], dtype='<f4'),
                    uv=np.array([[0, 0], [1, 0], [0, 1]], dtype='<f4'),
                    colors=np.full((3, 4), 255, dtype='u1'),
                    faces=np.array([[0, 1, 2]], dtype='<u4'))
               for i, (group, material) in enumerate(sorted(EXPECTED_ADDITIONS))]
    rows = peer_rows + [c.summarize(batch) for batch in gutters]
    manifest = copy.deepcopy(peer_manifest)
    manifest['features']['surface_refinement'] = True
    manifest['visualMeshCount'] = len(rows)
    manifest['visualTriangles'] = sum(record['triangles'] for record in rows)
    check = lambda value=rows, m=manifest: c.validate_summaries(value, m, baseline)
    tests.expect('positive', 'peer-only fixture preserved', lambda:
                 c.validate_summaries(peer_rows, peer_manifest, baseline))
    tests.expect('positive', 'both features accept exact eight additions', check)
    ok, detail = check()
    tests.expect('positive', 'exact total 1059, exact protected 603, exact roof additions 8', lambda:
                 ok and detail['expectedTotalBatches'] == detail['actualTotalBatches'] == 1059
                 and detail['actualProtectedBatches'] == detail['expectedProtectedBatches'] == 603
                 and detail['unchangedProtectedBatches'] == 595
                 and detail['expectedSurfaceRefinementBatches'] == detail['actualSurfaceRefinementBatches'] == 8)
    # No protected position/UV/Color32/index exemptions are introduced by the new flag.
    protected = ({c.key(record) for record in baseline['protectedGroups']} - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
    for index, row in enumerate(rows):
        if c.key(row) not in protected:
            continue
        changed = dict(row, attributesAndIndicesSha256='f' * 64)
        tests.expect('protected_payloads', str(c.key(row)) + ' still exact with surface flag', lambda
                     index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:]), False)
    for flag in (None, False, 0, 1, 'true', {}, []):
        changed = copy.deepcopy(manifest)
        changed['features']['surface_refinement'] = flag
        tests.expect('feature_gate', 'surface additions rejected without literal true: ' + repr(flag),
                     lambda changed=changed: check(m=changed), False)
        unchanged = copy.deepcopy(peer_manifest)
        unchanged['features']['surface_refinement'] = flag
        tests.expect('feature_gate', 'peer-only remains valid for disabled surface flag: ' + repr(flag), lambda
                     unchanged=unchanged: c.validate_summaries(peer_rows, unchanged, baseline))
    changed = copy.deepcopy(manifest)
    del changed['features']['surface_refinement']
    tests.expect('feature_gate', 'missing surface flag rejects new batches', lambda: check(m=changed), False)
    tests.expect('feature_gate', 'surface true requires all eight additions', lambda: check(peer_rows), False)
    for index in range(len(peer_rows), len(rows)):
        row = rows[index]
        tests.expect('gutter_roster', row['group'] + ' missing', lambda index=index:
                     check(rows[:index] + rows[index+1:]), False)
        tests.expect('gutter_roster', row['group'] + ' duplicate', lambda row=row: check(rows + [row]), False)
        for field, value in [('material', 'Copper'), ('material', 'Bark'),
                             ('group', row['group'] + '/Cell_0_0'),
                             ('group', row['group'].replace('/Joinery', '/Gutters'))]:
            changed = dict(row, **{field: value})
            tests.expect('gutter_roster', row['group'] + ' ' + field + '=' + value,
                         lambda index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:]), False)
    for group, material in [('Shops/S09/Joinery', 'RoofCopper'),
                            ('Shops/S01/Joinery', 'RoofCopperExtra'),
                            ('Landscape/DetailLeaves_Peer_East_Near/Cell_0_0', 'FoliageScenerySpray0')]:
        extra = dict(rows[-1], group=group, material=material)
        tests.expect('extra_groups', 'no ninth/wildcard addition ' + str((group, material)),
                     lambda extra=extra: check(rows + [extra]), False)
    for field in ('visualMeshCount', 'visualTriangles'):
        changed = copy.deepcopy(manifest)
        changed[field] -= 1
        tests.expect('manifest', field + ' mismatch rejected', lambda changed=changed: check(m=changed), False)
    with tempfile.TemporaryDirectory(prefix='surface-roster-fixture-') as directory:
        path = Path(directory) / 'VisualMeshes.bytes'
        write_visual(path, peer + gutters)
        tests.expect('actual_parser', 'actual binary path accepts exact gated surface roster', lambda:
                     c.validate_peer_culling(args.root, manifest, path))
        wrong = dict(gutters[-1], material='Copper')
        write_visual(path, peer + gutters[:-1] + [wrong])
        tests.expect('actual_parser', 'actual binary path rejects wrong new material', lambda:
                     c.validate_peer_culling(args.root, manifest, path), False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    tests = Tests()
    try:
        run(args, tests)
    except Exception as error:
        tests.failures.append(dict(test='suite setup', exception=type(error).__name__, error=str(error)))
    result = dict(status='FAIL' if tests.failures else 'PASS', count=tests.count,
                  categories=tests.categories, failures=tests.failures,
                  scope='Exact batch roster gating and unchanged protected payload contract; synthetic gutter geometry, not roof-art validation')
    print(json.dumps(result, indent=2))
    return bool(tests.failures)


if __name__ == '__main__':
    raise SystemExit(main())
