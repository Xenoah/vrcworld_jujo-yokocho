"""Narrow v2.7 -> v2.8 exceptions to the immutable v2.6 layout baseline.

This module never regenerates geometry or updates baselines. Only 16 counter
colliders, 12 lift-control position/size pairs and one reviewed Bark batch may
change. All other fields/records in those protected collections stay fixed.
"""
import hashlib
import json

import numpy as np


COLLISION_SHA256 = '51e395fbea8f6d29ffbebe76bb484f465c671508f93bf75afa9294ccff630ddb'
SOLID_BOX_BASELINE_SHA256 = '119008866d3725961468ac7740bbf8ea46362f20f75ffe7073518fda6823e79c'
LIFT_BASELINE_SHA256 = 'ba815a559872a8c06830de0e504da16c44406f15cd1e288bdc7a80414a08cec4'
BRANCH_KEY = ('Tree/SupportingBranches', 'Bark')
BRANCH_BEFORE_SHA256 = '193ef190f01988b59cf0198c9c4f42d45fed6b1bba5678f248495aa0fb896a71'
BRANCH_AFTER_SHA256 = '8f6573d1bb4f319d7998c5371aa0fb9b7c894b3e56982476ffdfceb87492c48d'
LIFT_LEVELS = ('G0', 'L1', 'L2', 'L3')


def metadata_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def intended_solid_box_changes(root, manifest):
    """Reuse the staff audit, adding baseline and whole-record schema guards."""
    from validate_staff_access import intended_counter_changes

    before = json.loads((root / 'Docs/baselines/verified_shop_solids_2.7.0.json').read_text())['solidBoxes']
    if metadata_sha256(before) != SOLID_BOX_BASELINE_SHA256:
        return False, {'reason': 'original 77-box baseline hash changed'}
    after = manifest.get('solidBoxes')
    if not isinstance(after, list) or len(after) != len(before):
        return False, {'reason': 'solid count changed; expected 77'}
    # The delegated counter helper checks authored center/size changes, but does
    # not reject added fields on its 16 edited boxes. Close that loophole here.
    errors = []
    trimmed_indices = {9 * shop + offset for shop in range(8) for offset in (7, 8)}
    for i, (old, new) in enumerate(zip(before, after)):
        if not isinstance(new, dict) or new.keys() != old.keys():
            errors.append({'index': i, 'reason': 'solid fields added or removed'})
            continue
        if i not in trimmed_indices:
            if metadata_sha256(old) != metadata_sha256(new):
                errors.append({'index': i, 'reason': 'unrelated solid changed'})
            continue
        immutable = {key: value for key, value in old.items() if key not in ('center', 'size')}
        observed = {key: value for key, value in new.items() if key not in ('center', 'size')}
        if metadata_sha256(immutable) != metadata_sha256(observed):
            errors.append({'index': i, 'reason': 'counter fields outside center/size changed'})
        for field in ('center', 'size'):
            vector = new[field]
            if (not isinstance(vector, list) or len(vector) != 3
                    or any(type(value) not in (int, float) for value in vector)):
                errors.append({'index': i, 'reason': 'invalid numeric counter ' + field})
    if errors:
        return False, {'errors': errors, 'allowedChangedBoxes': 16, 'unchangedOtherBoxes': 61}
    try:
        ok, detail = intended_counter_changes(root, manifest)
    except (KeyError, TypeError, ValueError) as error:
        return False, {'reason': 'invalid counter record', 'error': str(error)}
    detail['permittedFields'] = ['center', 'size']
    detail['baselineSha256'] = SOLID_BOX_BASELINE_SHA256
    return ok, detail


def intended_lift_control_changes(root, manifest):
    """Exactly 12 west-bank relocations; preserve every other control field."""
    before = json.loads((root / 'Docs/baselines/verified_lift_controls_2.7.0.json').read_text())['teleports']
    if len(before) != 12 or metadata_sha256(before) != LIFT_BASELINE_SHA256:
        return False, {'reason': 'original 12-control baseline hash changed'}
    after = manifest.get('teleports')
    if not isinstance(after, list) or len(after) != 12:
        return False, {'reason': 'lift control count changed; expected 12'}
    floors = manifest.get('floors', [])
    levels = {level: [floor.get('z') for floor in floors if floor.get('level') == level]
              for level in LIFT_LEVELS}
    if any(len(values) != 1 or type(values[0]) not in (int, float)
           or not np.isfinite(values[0]) for values in levels.values()):
        return False, {'reason': 'each source level needs one finite current floor height'}
    errors = []
    moved = []
    for i, (old, new) in enumerate(zip(before, after)):
        source, destination = old['name'].split('_To_')
        k = LIFT_LEVELS.index(destination)
        expected_position = [-17.20, -19.20 + k * .64, levels[source][0] + 1.25]
        expected_size = [.30, .58, .50]
        if not isinstance(new, dict) or new.keys() != old.keys():
            errors.append({'index': i, 'reason': 'control fields added or removed'})
            continue
        # Compare the full remaining record, not only selected known fields.
        immutable = {key: value for key, value in old.items() if key not in ('position', 'size')}
        observed = {key: value for key, value in new.items() if key not in ('position', 'size')}
        if metadata_sha256(immutable) != metadata_sha256(observed):
            errors.append({'index': i, 'reason': 'name/destination/forward/label or record order changed'})
        try:
            position = np.asarray(new['position'], dtype=float)
            size = np.asarray(new['size'], dtype=float)
            # Arithmetic-only tolerance accommodates -17.35 + .15 in the
            # generator; this is not a general geometry or placement margin.
            good = (isinstance(new['position'], list) and isinstance(new['size'], list)
                    and all(type(value) in (int, float) for value in new['position'] + new['size'])
                    and position.shape == (3,) and size.shape == (3,)
                    and np.allclose(position, expected_position, rtol=0, atol=1e-9)
                    and np.array_equal(size, expected_size))
        except (TypeError, ValueError):
            good = False
        if not good:
            errors.append({'index': i, 'reason': 'control differs from exact west-bank position/size',
                           'expectedPosition': expected_position, 'expectedSize': expected_size})
        moved.append({'name': old['name'], 'position': expected_position, 'size': expected_size})
    return not errors, {'baselineSha256': LIFT_BASELINE_SHA256, 'controls': moved,
                        'permittedFields': ['position', 'size'],
                        'unchangedFields': ['name', 'destination', 'forward', 'label'],
                        'positionArithmeticToleranceMetres': 1e-9, 'errors': errors}


def protected_group_hash_changes(base, actual_hashes):
    """Check all 599 protected hashes, permitting one exact reviewed replacement.

    actual_hashes maps (group, material) to a list of hashes, retaining duplicate
    batches rather than silently accepting the last copy of a protected batch.
    Hashes are little-endian float32 vertices followed by uint32 face indices.
    """
    records = base['protectedGroups']
    keys = [(record['group'], record['material']) for record in records]
    errors = []
    if len(records) != 599 or len(set(keys)) != 599:
        errors.append({'reason': 'expected 599 distinct baseline protected batches'})
    branch_records = [record for record in records
                      if (record['group'], record['material']) == BRANCH_KEY]
    if len(branch_records) != 1 or branch_records[0]['geometrySha256'] != BRANCH_BEFORE_SHA256:
        errors.append({'reason': 'SupportingBranches baseline is not the reviewed original hash'})
    drift = []
    for record in records:
        key = (record['group'], record['material'])
        expected = BRANCH_AFTER_SHA256 if key == BRANCH_KEY else record['geometrySha256']
        observed = actual_hashes.get(key, [])
        if observed != [expected]:
            drift.append(record['group'])
            errors.append({'group': key[0], 'material': key[1],
                           'expectedSha256': expected, 'actualSha256': observed})
    detail = {'baselineBatches': len(records), 'unchangedOtherBatches': 598,
              'hashConvention': 'little-endian float32 vertices then uint32 face indices',
              'exactPermittedReplacement': {'group': BRANCH_KEY[0], 'material': BRANCH_KEY[1],
                  'beforeSha256': BRANCH_BEFORE_SHA256, 'afterSha256': BRANCH_AFTER_SHA256},
              'driftedGroups': drift, 'errors': errors}
    return not errors, detail


def protected_geometry_changes(base, batches, *, manifest=None, root=None, visual_path=None):
    # Default/legacy calls retain the original v2.8 exact hash contract. Only a
    # literal manifest true selects the separately pinned, attribute-aware split.
    from peer_culling_contract import enabled, validate_peer_culling, OLD_KEYS, PEER_PREFIXES
    if manifest is not None and enabled(manifest):
        if root is None:
            return False, {'reason': 'peer split validation requires the pinned baseline root'}
        return validate_peer_culling(root, manifest, visual_path)
    unexpected = [(batch['group'], batch['material']) for batch in batches
                  if batch['group'].startswith(PEER_PREFIXES)
                  and (batch['group'], batch['material']) not in OLD_KEYS]
    if unexpected:
        return False, {'reason': 'Peer replacement requires features.peer_culling_split=true',
                       'unexpectedPeerBatches': unexpected}
    hashes = {}
    protected = {(record['group'], record['material']) for record in base['protectedGroups']}
    for batch in batches:
        key = (batch['group'], batch['material'])
        if key not in protected:
            continue
        raw = (np.asarray(batch['vertices'], dtype='<f4').tobytes()
               + np.asarray(batch['faces'], dtype='<u4').tobytes())
        hashes.setdefault(key, []).append(hashlib.sha256(raw).hexdigest())
    return protected_group_hash_changes(base, hashes)


def main_ring_route(manifest):
    """Use the authored XY route and Z when present; legacy circle only if absent."""
    if 'mainRingNavigation' not in manifest:
        points = [[18 * np.cos(a), 18 * np.sin(a), 140]
                  for a in np.linspace(0, 2 * np.pi, 241)]
        return np.asarray(points), 'legacy_circle'
    route = manifest['mainRingNavigation']
    if not isinstance(route, dict):
        raise ValueError('mainRingNavigation must contain points and z')
    xy = np.asarray(route.get('points'), dtype=float)
    z = route.get('z')
    if (xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 2 or not np.isfinite(xy).all()
            or type(z) not in (int, float) or not np.isfinite(z)):
        raise ValueError('mainRingNavigation needs at least two finite XY points and a finite z')
    return np.column_stack([xy, np.full(len(xy), z)]), 'manifest.mainRingNavigation'
