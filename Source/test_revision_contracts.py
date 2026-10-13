"""Read-only positive/adversarial regression tests for the exact v2.8 deltas.

Usage: python Source/test_revision_contracts.py [project_root]
Prints one compact JSON result and exits nonzero on failure. All mutations are
in-memory fixtures; no world regeneration, baseline changes or report writes.
"""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Keep even test imports from writing repository-local bytecode caches.
sys.dont_write_bytecode = True

import numpy as np


EXPECTED_ASSERTIONS = 2345
LAYOUT_FILE_SHA256 = '5d58e8c0c6cd6605e7ae54d2cffbd725214417d61166c13f6a4ce441cb7b8324'
COLLISION_FILE_SHA256 = '51e395fbea8f6d29ffbebe76bb484f465c671508f93bf75afa9294ccff630ddb'
BRANCH_KEY = ('Tree/SupportingBranches', 'Bark')
BRANCH_AFTER_SHA256 = '8f6573d1bb4f319d7998c5371aa0fb9b7c894b3e56982476ffdfceb87492c48d'


class Assertions:
    def __init__(self):
        self.count = 0
        self.failures = []

    def expect(self, label, callback, expected=True):
        self.count += 1
        try:
            result = callback()
            passed = result[0] if isinstance(result, tuple) else result
            if bool(passed) != expected:
                self.failures.append({'test': label, 'expected': expected, 'actual': result})
        except Exception as error:
            self.failures.append({'test': label, 'exception': type(error).__name__, 'error': str(error)})

    def rejects_route(self, label, callback):
        self.count += 1
        try:
            callback()
        except (TypeError, ValueError):
            return
        except Exception as error:
            self.failures.append({'test': label, 'exception': type(error).__name__, 'error': str(error)})
        else:
            self.failures.append({'test': label, 'error': 'malformed authored route was accepted'})


def run_suite(root, assertions):
    sys.path.insert(0, str(root / 'Source'))
    import revision_contracts as contracts

    manifest = json.loads((root / 'Assets/TreeTopYokocho/Data/WorldManifest.json').read_text())
    base = json.loads((root / 'Docs/baselines/verified_layout_2.6.0.json').read_text())
    old = {
        'floors': manifest['floors'],
        'solidBoxes': json.loads((root / 'Docs/baselines/verified_shop_solids_2.7.0.json').read_text())['solidBoxes'],
        'teleports': json.loads((root / 'Docs/baselines/verified_lift_controls_2.7.0.json').read_text())['teleports'],
    }
    good = copy.deepcopy(old)
    trimmed_indices = [9 * shop + offset for shop in range(8) for offset in (7, 8)]
    # Deliberately spell out the reviewed .30 m left-side trim rather than
    # deriving the fixture from the validator or mutable authoring constants.
    for index in trimmed_indices:
        box = good['solidBoxes'][index]
        box['center'] = (np.asarray(box['center']) + np.asarray(box['axes'][:3]) * .15).tolist()
        box['size'] = (np.asarray(box['size']) - [.30, 0, 0]).tolist()
    levels = {floor['level']: floor['z'] for floor in good['floors']}
    for control in good['teleports']:
        source, destination = control['name'].split('_To_')
        index = ('G0', 'L1', 'L2', 'L3').index(destination)
        control['position'] = [-17.35 + .15, -19.20 + index * .64, levels[source] + 1.25]
        control['size'] = [.30, .58, .50]

    expect = assertions.expect

    def mutation(label, collection, index, edit, validator):
        bad = copy.deepcopy(good)
        edit(bad[collection][index])
        expect(f'{collection}[{index}] {label}', lambda: validator(root, bad), False)

    # 532 metadata assertions: exact positive fixtures and every record's
    # prohibited extra/missing fields, with count/order/value/type mutations.
    for key, validator in [('solidBoxes', contracts.intended_solid_box_changes),
                           ('teleports', contracts.intended_lift_control_changes)]:
        expect('correct authored ' + key, lambda v=validator: v(root, good))
        expect('unchanged old ' + key + ' rejected', lambda v=validator: v(root, old), False)
        for index in range(len(good[key])):
            mutation('extra field', key, index, lambda record: record.update(extra=True), validator)
            mutation('missing field', key, index, lambda record: record.pop('name'), validator)
        for action in ('append', 'delete', 'reorder'):
            bad = copy.deepcopy(good)
            if action == 'append':
                bad[key].append(copy.deepcopy(bad[key][0]))
            elif action == 'delete':
                bad[key].pop()
            else:
                bad[key][0], bad[key][1] = bad[key][1], bad[key][0]
            expect(key + ' ' + action, lambda v=validator, value=bad: v(root, value), False)

    for index in range(77):
        mutation('unauthorized center drift', 'solidBoxes', index,
                 lambda record: record['center'].__setitem__(2, record['center'][2] + .001),
                 contracts.intended_solid_box_changes)
        mutation('axes zero replaced by boolean', 'solidBoxes', index,
                 lambda record: record['axes'].__setitem__(2, False), contracts.intended_solid_box_changes)
    for index in trimmed_indices:
        for field in ('name', 'axes', 'size'):
            def edit(record, field=field):
                if field == 'name':
                    record[field] += '_changed'
                else:
                    record[field][0] += .001
            mutation('wrong counter ' + field, 'solidBoxes', index, edit,
                     contracts.intended_solid_box_changes)
        mutation('counter coordinate replaced by string', 'solidBoxes', index,
                 lambda record: record['center'].__setitem__(0, str(record['center'][0])),
                 contracts.intended_solid_box_changes)

    edits = [
        ('name changed', lambda c: c.update(name=c['name'] + '_x')),
        ('label changed', lambda c: c.update(label='changed')),
        ('destination changed', lambda c: c['destination'].__setitem__(2, c['destination'][2] + .001)),
        ('forward changed', lambda c: c['forward'].__setitem__(0, 1)),
        ('position changed', lambda c: c['position'].__setitem__(0, c['position'][0] + .001)),
        ('size changed', lambda c: c['size'].__setitem__(0, c['size'][0] + .001)),
        ('position string', lambda c: c['position'].__setitem__(0, str(c['position'][0]))),
        ('size string', lambda c: c['size'].__setitem__(0, str(c['size'][0]))),
        ('nonfinite position', lambda c: c['position'].__setitem__(0, float('nan'))),
        ('extra position coordinate', lambda c: c['position'].append(0)),
    ]
    for index in range(12):
        for label, edit in edits:
            mutation(label, 'teleports', index, edit, contracts.intended_lift_control_changes)
    for action in ('missing floor', 'duplicate floor', 'wrong floor height', 'nonfinite floor height'):
        bad = copy.deepcopy(good)
        if action == 'missing floor':
            bad['floors'] = [floor for floor in bad['floors'] if floor['level'] != 'G0']
        elif action == 'duplicate floor':
            bad['floors'].append(copy.deepcopy(bad['floors'][0]))
        elif action == 'wrong floor height':
            bad['floors'][0]['z'] += 1
        else:
            bad['floors'][0]['z'] = float('inf')
        expect(action, lambda value=bad: contracts.intended_lift_control_changes(root, value), False)

    # Corrupt baseline reads only inside a context manager; never write files.
    original_read = Path.read_text
    for key, filename, validator in [
        ('solidBoxes', 'verified_shop_solids_2.7.0.json', contracts.intended_solid_box_changes),
        ('teleports', 'verified_lift_controls_2.7.0.json', contracts.intended_lift_control_changes),
    ]:
        def changed_read(path, *args, key=key, filename=filename, **kwargs):
            value = original_read(path, *args, **kwargs)
            if path.name == filename:
                data = json.loads(value)
                data[key][0]['name'] += 'changed'
                return json.dumps(data)
            return value
        with patch.object(Path, 'read_text', changed_read):
            expect(key + ' modified baseline rejected', lambda v=validator: v(root, good), False)

    # 1,802 protected-geometry assertions. Synthetic hash lists exercise the
    # permission contract; actual exported bytes are checked by the shop audit.
    hashes = {(record['group'], record['material']): [record['geometrySha256']]
              for record in base['protectedGroups']}
    expect('old branch rejected', lambda: contracts.protected_group_hash_changes(base, hashes), False)
    hashes[BRANCH_KEY] = [BRANCH_AFTER_SHA256]
    expect('reviewed branch accepted', lambda: contracts.protected_group_hash_changes(base, hashes))
    for key in hashes:
        for label, value in [('missing', []), ('changed', ['0' * 64]), ('duplicate', hashes[key] * 2)]:
            bad = dict(hashes)
            bad[key] = value
            expect(f'protected {key[0]}/{key[1]} {label}',
                   lambda value=bad: contracts.protected_group_hash_changes(base, value), False)
    for action in ('missing', 'duplicate', 'old branch hash changed'):
        bad = copy.deepcopy(base)
        if action == 'missing':
            bad['protectedGroups'].pop()
        elif action == 'duplicate':
            bad['protectedGroups'][1] = copy.deepcopy(bad['protectedGroups'][0])
        else:
            record = next(record for record in bad['protectedGroups']
                          if (record['group'], record['material']) == BRANCH_KEY)
            record['geometrySha256'] = 'f' * 64
        expect('protected baseline ' + action,
               lambda value=bad: contracts.protected_group_hash_changes(value, hashes), False)

    # Nine routing assertions: two positives plus seven malformed authored
    # routes that must fail rather than silently using the legacy circle.
    points, source = contracts.main_ring_route({})
    expect('absent authored ring uses legacy circle',
           lambda: source == 'legacy_circle' and points.shape == (241, 3) and (points[:, 2] == 140).all())
    points, source = contracts.main_ring_route(
        {'mainRingNavigation': {'points': [[1, 2], [3, 4], [5, 6]], 'z': 147.5}})
    expect('authored XY/Z used exactly', lambda: source == 'manifest.mainRingNavigation'
           and np.array_equal(points, [[1, 2, 147.5], [3, 4, 147.5], [5, 6, 147.5]]))
    invalid_routes = [
        ('null', None), ('missing fields', {}), ('empty points', {'points': [], 'z': 140}),
        ('single point', {'points': [[1, 2]], 'z': 140}),
        ('XYZ instead of XY', {'points': [[1, 2, 3], [4, 5, 6]], 'z': 140}),
        ('nonfinite Z', {'points': [[1, 2], [3, 4]], 'z': float('nan')}),
        ('nonfinite XY', {'points': [[float('inf'), 2], [3, 4]], 'z': 140}),
    ]
    for label, invalid in invalid_routes:
        assertions.rejects_route('invalid authored ring: ' + label,
                                 lambda value=invalid: contracts.main_ring_route({'mainRingNavigation': value}))

    # Two immutable-input assertions are independently pinned, not copied from
    # the implementation constants under test.
    expect('original layout baseline preserved', lambda: hashlib.sha256(
        (root / 'Docs/baselines/verified_layout_2.6.0.json').read_bytes()).hexdigest() == LAYOUT_FILE_SHA256)
    expect('collision unchanged', lambda: hashlib.sha256(
        (root / 'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes').read_bytes()).hexdigest() == COLLISION_FILE_SHA256)


def main(root):
    started = time.time()
    assertions = Assertions()
    try:
        run_suite(Path(root).resolve(), assertions)
    except Exception as error:
        assertions.failures.append({'test': 'suite setup/execution',
                                    'exception': type(error).__name__, 'error': str(error)})
    if assertions.count != EXPECTED_ASSERTIONS:
        assertions.failures.append({'test': 'assertion count',
                                    'expected': EXPECTED_ASSERTIONS, 'actual': assertions.count})
    result = {
        'status': 'FAIL' if assertions.failures else 'PASS',
        'count': assertions.count,
        'expectedCount': EXPECTED_ASSERTIONS,
        'failures': assertions.failures,
        'expectedCoverage': {'metadata': 532, 'protectedGeometry': 1802, 'mainRing': 9, 'immutableInputs': 2},
        'scope': 'In-memory contract fixtures; no regeneration or repository/report writes',
        'seconds': round(time.time() - started, 3),
    }
    print(json.dumps(result, separators=(',', ':'), default=str))
    return bool(assertions.failures)


if __name__ == '__main__':
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent))
