"""Read-only positive/malicious-mutation tests for the pinned source split.

Use --actual with a current export, or provide the frozen v2.8/partition fixtures.
No world build is performed.
All adversarial changes are in memory or temporary files, never the repository.
"""
import argparse
import copy
import hashlib
import json
import struct
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
import numpy as np
import peer_culling_contract as c
import revision_contracts

PINNED_BASELINE_SHA256 = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'


class Tests:
    def __init__(self):
        self.count = 0
        self.failures = []
        self.categories = {}

    def expect(self, category, label, fn, expected=True):
        self.count += 1
        self.categories[category] = self.categories.get(category, 0) + 1
        try:
            value = fn()
            actual = value[0] if isinstance(value, tuple) else value
            if bool(actual) != expected:
                self.failures.append(dict(test=label, expected=expected, actual=value))
        except Exception as error:
            self.failures.append(dict(test=label, error=str(error), exception=type(error).__name__))


def run(args, tests):
    baseline = c.load_baseline(args.root)
    old = c.read_visual(args.frozen / 'VisualMeshes.bytes')
    candidate = c.read_visual(args.fixture / 'frozen_v28_induced_split.bytes')
    manifest = json.loads((args.fixture / 'frozen_v28_induced_split_manifest.json').read_text())
    old_manifest = json.loads((args.frozen / 'WorldManifest.json').read_text())
    layout = json.loads((args.root / 'Docs/baselines/verified_layout_2.6.0.json').read_text())
    summaries = [c.summarize(batch) for batch in candidate]
    lookup = {c.key(record): i for i, record in enumerate(summaries)}
    protected = {c.key(record) for record in baseline['protectedGroups']} - set(c.OLD_KEYS)
    protected.update(c.NEW_TO_OLD)
    check = lambda rows=summaries, m=manifest: c.validate_summaries(rows, m, baseline)
    tests.expect('positive', 'unchanged correct fixture', check)
    tests.expect('positive', 'deep copied unchanged correct fixture', lambda: check(copy.deepcopy(summaries)))
    tests.expect('positive', 'future actual binary passes source validator',
                 lambda: c.validate_peer_culling(args.root, manifest, args.fixture / 'frozen_v28_induced_split.bytes'))
    tests.expect('positive', 'v2.8 actual frozen payload keeps old contract',
                 lambda: revision_contracts.protected_geometry_changes(layout, old, manifest=old_manifest))
    tests.expect('positive', 'legacy signature keeps old contract',
                 lambda: revision_contracts.protected_geometry_changes(layout, old))
    tests.expect('positive', 'future wrapper reads actual export attributes', lambda:
        revision_contracts.protected_geometry_changes(layout, candidate, manifest=manifest,
            root=args.root, visual_path=args.fixture / 'frozen_v28_induced_split.bytes'))
    tests.expect('pinning', 'baseline independently pinned file bytes', lambda: hashlib.sha256(
        (args.root / 'Docs/baselines' / c.BASELINE_NAME).read_bytes()).hexdigest() == PINNED_BASELINE_SHA256)
    tests.expect('pinning', 'other 595 include exact reviewed branch', lambda: next(
        row for row in baseline['protectedGroups'] if c.key(row) == c.BRANCH_KEY)['geometrySha256'] ==
        '8f6573d1bb4f319d7998c5371aa0fb9b7c894b3e56982476ffdfceb87492c48d')

    # Each of all 603 protected batches is independently missing, duplicated,
    # and changed. No last-write-wins dictionary can hide duplicate batches.
    for k in sorted(protected):
        index = lookup[k]
        tests.expect('all_protected_mutations', str(k) + ' missing',
                     lambda i=index: check(summaries[:i] + summaries[i+1:]), False)
        tests.expect('all_protected_mutations', str(k) + ' duplicate',
                     lambda i=index: check(summaries + [summaries[i]]), False)
        changed = dict(summaries[index], attributesAndIndicesSha256='0' * 64)
        tests.expect('all_protected_mutations', str(k) + ' attribute/index change',
                     lambda i=index, changed=changed: check(summaries[:i] + [changed] + summaries[i+1:]), False)

    for flag in (None, False, 0, 1, 'true', {}, []):
        m = copy.deepcopy(manifest)
        m['features']['peer_culling_split'] = flag
        tests.expect('feature_gate', 'only literal true accepted: ' + repr(flag), lambda m=m: check(m=m), False)
        tests.expect('feature_gate', 'wrapper rejects split under flag ' + repr(flag), lambda m=m:
                     revision_contracts.protected_geometry_changes(layout, candidate, manifest=m), False)
    m = copy.deepcopy(manifest)
    del m['features']['peer_culling_split']
    tests.expect('feature_gate', 'absent flag rejects split', lambda: check(m=m), False)
    tests.expect('feature_gate', 'old groups under true rejected',
                 lambda: check([c.summarize(batch) for batch in old]), False)
    tests.expect('feature_gate', 'root needed for true feature', lambda:
                 revision_contracts.protected_geometry_changes(layout, candidate, manifest=manifest), False)
    for field in ('visualMeshCount', 'visualTriangles'):
        m = copy.deepcopy(manifest)
        m[field] += 1
        tests.expect('manifest', field + ' wrong count', lambda m=m: check(m=m), False)
        m = copy.deepcopy(manifest)
        del m[field]
        tests.expect('manifest', field + ' missing', lambda m=m: check(m=m), False)

    template = summaries[lookup[next(iter(c.NEW_TO_OLD))]]
    additions = [
        ('Landscape/DetailLeaves_Peer_East_Near/Cell_0_0', 'FoliageScenerySpray0'),
        ('Landscape/DetailLeaves_Peer_Near/Cell_-1_2', 'FoliageScenerySpray0'),
        ('Landscape/DetailTwigs_Peer_East_Far', 'Bark'),
        ('Landscape/DetailLeaves_Peer_East_Near', 'UnapprovedMaterial'),
        ('Landscape/DetailLeaves_Peer_North_Near', 'FoliageScenerySpray0'),
        ('Tree/SupportingBranches/Cell_0_0', 'Bark'),
        ('Tree/SupportingBranches', 'UnapprovedMaterial'),
        ('Entirely/NewExtraBatch', 'Bark'),
    ] + list(c.OLD_KEYS)
    for group, material in additions:
        changed = dict(template, group=group, material=material)
        tests.expect('extra_groups', group + '/' + material, lambda changed=changed: check(summaries + [changed]), False)
    for new, old_key in c.NEW_TO_OLD.items():
        tests.expect('normalization', 'explicit pair folds: ' + str(new), lambda new=new, old_key=old_key:
                     c.canonical_key(*new) == old_key)
    for pair in additions[:8]:
        tests.expect('normalization', 'unknown pair never folds: ' + str(pair), lambda pair=pair:
                     c.canonical_key(*pair) == pair)

    # Real attribute arrays are mutated and re-hashed, rather than trusting
    # synthetic failure hashes for the exact eight replacement batches.
    for pair in sorted(c.NEW_TO_OLD):
        index = lookup[pair]
        original = candidate[index]
        for mutation in ('position_ulp', 'uv_ulp', 'color_bit', 'reversed_winding',
                         'duplicated_triangle', 'removed_triangle', 'extra_unused_vertex',
                         'split_shared_vertex', 'swapped_east_west'):
            changed = dict(original)
            changed.update({field: original[field].copy() for field in ('vertices', 'uv', 'colors', 'faces')})
            if mutation == 'position_ulp':
                changed['vertices'][0, 0] = np.nextafter(changed['vertices'][0, 0], np.float32(np.inf))
            elif mutation == 'uv_ulp':
                changed['uv'][0, 0] = np.nextafter(changed['uv'][0, 0], np.float32(np.inf))
            elif mutation == 'color_bit':
                changed['colors'][0, 0] ^= 1
            elif mutation == 'reversed_winding':
                changed['faces'][0] = changed['faces'][0, [0, 2, 1]]
            elif mutation == 'duplicated_triangle':
                changed['faces'] = np.concatenate([changed['faces'], changed['faces'][:1]])
            elif mutation == 'removed_triangle':
                changed['faces'] = changed['faces'][1:]
            elif mutation in ('extra_unused_vertex', 'split_shared_vertex'):
                vertex = int(changed['faces'][0, 0])
                for field in ('vertices', 'uv', 'colors'):
                    changed[field] = np.concatenate([changed[field], changed[field][vertex:vertex+1]])
                if mutation == 'split_shared_vertex':
                    changed['faces'][0, 0] = len(changed['vertices']) - 1
                    tests.expect('topology', 'triangle multiset misses shared-vertex mutation: ' + str(pair),
                                 lambda changed=changed, original=original:
                                 c.triangle_fingerprint([changed]) == c.triangle_fingerprint([original]))
            else:
                changed['group'] = changed['group'].replace('_East_', '_TEMP_').replace('_West_', '_East_').replace('_TEMP_', '_West_')
            rows = summaries[:index] + [c.summarize(changed)] + summaries[index+1:]
            tests.expect('real_array_mutations', str(pair) + ' ' + mutation, lambda rows=rows: check(rows), False)

    # Exact unmodified fixture equivalence plus full-array partition order from
    # the original procedural proposal, kept separate from current frozen data.
    if args.proposal:
        before = c.read_visual(args.proposal / 'original_forest_fixture.bytes')
        after = c.read_visual(args.proposal / 'regrouped_forest_fixture.bytes')
        after_map = {c.key(batch): batch for batch in after}
        expected_keys = ({c.key(batch) for batch in before} - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
        tests.expect('proposal_fixture', 'exact proposal fixture roster without duplicate batches',
                     lambda: set(after_map) == expected_keys and len(after_map) == len(after))
        for batch in before:
            if c.key(batch) not in c.OLD_KEYS:
                tests.expect('proposal_fixture', 'unchanged other fixture batch ' + str(c.key(batch)),
                             lambda batch=batch: c.summarize(batch) == c.summarize(after_map[c.key(batch)]))
                continue
            parts = c.partition_peer(batch)
            actual = [after_map[c.key(part)] for part in parts]
            tests.expect('proposal_fixture', 'exact oriented triangle attributes ' + str(c.key(batch)),
                         lambda batch=batch, actual=actual: c.triangle_fingerprint([batch]) == c.triangle_fingerprint(actual))
            for part in parts:
                tests.expect('proposal_fixture', 'exact per-side indexed payload ' + str(c.key(part)),
                             lambda part=part: c.summarize(part) == c.summarize(after_map[c.key(part)]))

    actual_read = Path.read_bytes
    def corrupt_baseline(path):
        raw = actual_read(path)
        return raw + b' ' if path.name == c.BASELINE_NAME else raw
    with patch.object(Path, 'read_bytes', corrupt_baseline):
        tests.expect('pinning', 'even whitespace baseline tampering fails', lambda:
                     c.validate_peer_culling(args.root, manifest, args.fixture / 'frozen_v28_induced_split.bytes'), False)
    with tempfile.TemporaryDirectory(prefix='peer-malformed-') as directory:
        path = Path(directory) / 'bad.bytes'
        for label, raw in [('empty', b''), ('wrong_signature', b'XXXX' + struct.pack('<II', 1, 0)),
                           ('wrong_version', b'JYWM' + struct.pack('<II', 2, 0)),
                           ('truncated', b'JYWM' + struct.pack('<II', 1, 1)),
                           ('trailing', b'JYWM' + struct.pack('<II', 1, 0) + b'junk'),
                           ('huge_name_length', b'JYWM' + struct.pack('<III', 1, 1, 0xffffffff))]:
            path.write_bytes(raw)
            tests.expect('binary_reader', label, lambda: c.validate_peer_culling(args.root, manifest, path), False)


def run_actual(args, tests):
    """Self-contained current-export checks; no external frozen fixtures needed."""
    data = args.root / 'Assets/TreeTopYokocho/Data'
    baseline = c.load_baseline(args.root)
    manifest = json.loads((data / 'WorldManifest.json').read_text())
    batches = c.read_visual(data / 'VisualMeshes.bytes')
    rows = [c.summarize(batch) for batch in batches]
    check = lambda value=rows, m=manifest: c.validate_summaries(value, m, baseline)
    tests.expect('actual_export', 'current exported bytes satisfy pinned contract', check)
    tests.expect('pinning', 'independently pinned baseline file', lambda: hashlib.sha256(
        (args.root / 'Docs/baselines' / c.BASELINE_NAME).read_bytes()).hexdigest() == PINNED_BASELINE_SHA256)
    protected = ({c.key(row) for row in baseline['protectedGroups']} - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
    tests.expect('actual_export', 'exact 603 protected identities', lambda:
                 len(protected) == 603 and sum(c.key(row) in protected for row in rows) == 603)
    # Reuse real-export summaries to independently exercise each immutable entry.
    for index, row in enumerate(rows):
        if c.key(row) not in protected:
            continue
        tests.expect('all_protected_mutations', str(c.key(row)) + ' missing',
                     lambda index=index: check(rows[:index] + rows[index+1:]), False)
        tests.expect('all_protected_mutations', str(c.key(row)) + ' duplicated',
                     lambda row=row: check(rows + [row]), False)
        changed = dict(row, attributesAndIndicesSha256='0' * 64)
        tests.expect('all_protected_mutations', str(c.key(row)) + ' attributes/index changed', lambda
                     index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:]), False)
    for index, original in enumerate(batches):
        if c.key(original) not in set(c.NEW_TO_OLD) | {c.BRANCH_KEY}:
            continue
        for mutation in ('position_ulp', 'uv_ulp', 'color_bit', 'reversed_winding',
                         'duplicated_triangle', 'split_shared_vertex'):
            changed = dict(original)
            changed.update({field: original[field].copy() for field in ('vertices', 'uv', 'colors', 'faces')})
            vertex = int(changed['faces'][0, 0])
            if mutation == 'position_ulp':
                changed['vertices'][vertex, 0] = np.nextafter(changed['vertices'][vertex, 0], np.float32(np.inf))
            elif mutation == 'uv_ulp':
                changed['uv'][vertex, 0] = np.nextafter(changed['uv'][vertex, 0], np.float32(np.inf))
            elif mutation == 'color_bit':
                changed['colors'][vertex, 0] ^= 1
            elif mutation == 'reversed_winding':
                changed['faces'][0] = changed['faces'][0, [0, 2, 1]]
            elif mutation == 'duplicated_triangle':
                changed['faces'] = np.concatenate([changed['faces'], changed['faces'][:1]])
            else:
                for field in ('vertices', 'uv', 'colors'):
                    changed[field] = np.concatenate([changed[field], changed[field][vertex:vertex+1]])
                changed['faces'][0, 0] = len(changed['vertices']) - 1
                tests.expect('topology', str(c.key(original)) + ' triangle-only hash misses split vertex',
                             lambda changed=changed, original=original:
                             c.triangle_fingerprint([changed]) == c.triangle_fingerprint([original]))
            changed_rows = rows[:index] + [c.summarize(changed)] + rows[index+1:]
            tests.expect('real_array_mutations', str(c.key(original)) + ' ' + mutation,
                         lambda changed_rows=changed_rows: check(changed_rows), False)
    for group, material in [('Landscape/DetailLeaves_Peer_East_Near/Cell_0_0', 'FoliageScenerySpray0'),
                            ('Landscape/DetailTwigs_Peer_West_Far', 'Bark'),
                            ('Shops/S09/Joinery', 'RoofCopper')]:
        extra = dict(rows[0], group=group, material=material)
        tests.expect('extra_groups', str((group, material)) + ' rejected', lambda extra=extra: check(rows+[extra]), False)
    for flag in (None, False, 1, 'true'):
        changed_manifest = copy.deepcopy(manifest)
        changed_manifest.setdefault('features', {})['peer_culling_split'] = flag
        tests.expect('feature_gate', 'peer split literal true required: ' + repr(flag),
                     lambda changed_manifest=changed_manifest: check(m=changed_manifest), False)
    if manifest.get('features', {}).get('surface_refinement') is True:
        for index, row in enumerate(rows):
            if c.key(row) not in set(c.SURFACE_REFINEMENT_BATCHES):
                continue
            tests.expect('surface_roster', str(c.key(row)) + ' missing', lambda index=index:
                         check(rows[:index] + rows[index+1:]), False)
            tests.expect('surface_roster', str(c.key(row)) + ' duplicate', lambda row=row: check(rows+[row]), False)
            changed = dict(row, material='UnapprovedRoofMaterial')
            tests.expect('surface_roster', str(c.key(row)) + ' wrong material', lambda index=index, changed=changed:
                         check(rows[:index] + [changed] + rows[index+1:]), False)
        for flag in (None, False, 1, 'true'):
            changed_manifest = copy.deepcopy(manifest)
            changed_manifest['features']['surface_refinement'] = flag
            tests.expect('feature_gate', 'surface literal true required: ' + repr(flag), lambda
                         changed_manifest=changed_manifest: check(m=changed_manifest), False)
    for field in ('visualMeshCount', 'visualTriangles'):
        changed_manifest = copy.deepcopy(manifest)
        changed_manifest[field] += 1
        tests.expect('manifest', field + ' mismatch rejected',
                     lambda changed_manifest=changed_manifest: check(m=changed_manifest), False)

    # Exercise the herb roster against current exported summaries even before
    # integration. The helper explicitly labels synthetic roster-only fixtures.
    from test_herb_planter_roster_contract import run_roster_cases
    run_roster_cases(rows, manifest, baseline, tests)

    from test_scenery_revision_contract import run_scenery_cases
    run_scenery_cases(rows, manifest, baseline, tests, batches=batches, root=args.root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--report', type=Path, help='Write the result from this actual execution')
    parser.add_argument('--actual', action='store_true', help='Use current exported bytes; no external fixtures')
    parser.add_argument('--frozen', type=Path)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--proposal', type=Path)
    args = parser.parse_args()
    if not args.actual and (args.frozen is None or args.fixture is None):
        parser.error('fixture mode needs --frozen and --fixture; use --actual for a current export')
    started = time.time()
    tests = Tests()
    try:
        (run_actual if args.actual else run)(args, tests)
    except Exception as error:
        tests.failures.append(dict(test='suite setup', error=str(error), exception=type(error).__name__))
    result = dict(status='FAIL' if tests.failures else 'PASS', count=tests.count,
                  categories=tests.categories, failures=tests.failures,
                  seconds=round(time.time()-started, 3),
                  scope=('Read-only current export plus in-memory adversarial mutations; no external fixtures, regeneration or Unity render'
                         if args.actual else 'Read-only actual binary fixture plus in-memory adversarial mutations; no regeneration or Unity render'))
    if args.report:args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return bool(tests.failures)


if __name__ == '__main__':
    raise SystemExit(main())
