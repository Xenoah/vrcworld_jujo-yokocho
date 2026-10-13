"""Current-export adversarial checks for the exact opt-in herb batch roster.

No world regeneration or baseline writes. Missing historical/replacement summary
rows are synthetic identity fixtures, explicitly not an integrated geometry test.
Recount every malicious roster so rejection cannot rely on stale manifest totals.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import peer_culling_contract as c

# Independent test oracle: never derive approved identities from the contract.
SHOP_CLAY = (
    ('Shops/S01', 'HerbClayOchre'), ('Shops/S02', 'HerbClayOchre'),
    ('Shops/S03', 'HerbClayUmber'), ('Shops/S04', 'HerbClayUmber'),
    ('Shops/S05', 'HerbClayOchre'), ('Shops/S06', 'HerbClayOchre'),
    ('Shops/S07', 'HerbClayUmber'), ('Shops/S08', 'HerbClayUmber'),
)
ADDED = {(group, material) for group, clay in SHOP_CLAY
         for material in ('HerbSoil', 'HerbLeafDeep', 'HerbLeafYoung', clay)}
REMOVED = {(group, material) for group, _ in SHOP_CLAY
           for material in ('Food', 'Foliage0', 'Foliage1', 'Foliage2', 'Foliage3')}
ROOFS = {(group + '/Joinery', 'RoofCopper') for group, _ in SHOP_CLAY}


def counted_manifest(rows, manifest):
    result = dict(manifest)
    result['visualMeshCount'] = len(rows)
    result['visualTriangles'] = sum(row['triangles'] for row in rows)
    return result


def run_roster_cases(current_rows, current_manifest, baseline, tests):
    """Run against a current export before OR after herb integration."""
    # This historical herb matrix intentionally starts before stage additions.
    # Normalize only the separately approved four identities/flag so this helper
    # and its standalone CLI keep working after craft integration. Snow's active
    # exact color state and all original stage records remain present.
    stage_keys = set(c.STAGE_ROOF_CRAFT_BATCHES)
    current_rows = [row for row in current_rows if c.key(row) not in stage_keys]
    current_manifest = copy.deepcopy(current_manifest)
    current_manifest.setdefault('features', {}).pop('stage_roof_craft', None)
    check = lambda rows, manifest: c.validate_summaries(
        rows, counted_manifest(rows, manifest), baseline)
    tests.expect('herb_pinning', 'exact 40 old identities and 32 new identities', lambda:
                 set(c.HERB_PLANTER_REMOVED_BATCHES) == REMOVED
                 and len(c.HERB_PLANTER_REMOVED_BATCHES) == 40
                 and set(c.HERB_PLANTER_ADDED_BATCHES) == ADDED
                 and len(c.HERB_PLANTER_ADDED_BATCHES) == 32)
    protected = ({c.key(row) for row in baseline['protectedGroups']} - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
    tests.expect('herb_pinning', 'no protected entries removed or replaced', lambda:
                 not (REMOVED | ADDED) & protected)
    tests.expect('herb_pinning', 'no new groups introduced', lambda:
                 {group for group, _ in ADDED} == {group for group, _ in REMOVED})

    # Use real current-export records where present; synthesize only the absent
    # unprotected identities. Hashes on those rows prove no herb geometry claim.
    actual = {c.key(row): row for row in current_rows}
    template = next(row for row in current_rows if c.key(row) not in protected)
    def identity(pair):
        return actual.get(pair, dict(template, group=pair[0], material=pair[1]))
    base = [row for row in current_rows if c.key(row) not in ADDED | REMOVED | ROOFS]
    legacy_rows = base + [identity(pair) for pair in sorted(REMOVED)]
    botanical_rows = base + [identity(pair) for pair in sorted(ADDED)]
    manifest = copy.deepcopy(current_manifest)
    manifest.setdefault('features', {})['peer_culling_split'] = True
    manifest['features'].pop('herb_planters', None)
    manifest['features'].pop('surface_refinement', None)
    tests.expect('herb_compatibility', 'peer-only roster path remains exact 1051', lambda:
                 len(legacy_rows) == 1051 and check(legacy_rows, manifest)[0])
    with_surface = copy.deepcopy(manifest)
    with_surface['features']['surface_refinement'] = True
    roof_rows = [identity(pair) for pair in sorted(ROOFS)]
    tests.expect('herb_compatibility', 'v2.9 roster path remains exact 1059', lambda:
                 len(legacy_rows + roof_rows) == 1059 and check(legacy_rows + roof_rows, with_surface)[0])
    enabled = copy.deepcopy(with_surface)
    enabled['features']['herb_planters'] = True
    rows = botanical_rows + roof_rows
    ok, detail = check(rows, enabled)
    tests.expect('herb_positive', 'three literal features require exact 1051, 603 protected, 32 herbs, 8 roofs', lambda:
                 ok and detail['expectedTotalBatches'] == detail['actualTotalBatches'] == 1051
                 and detail['expectedProtectedBatches'] == detail['actualProtectedBatches'] == 603
                 and detail['expectedHerbPlanterBatches'] == detail['actualHerbPlanterBatches'] == 32
                 and detail['expectedLegacyPlantBatches'] == detail['actualLegacyPlantBatches'] == 0
                 and detail['expectedSurfaceRefinementBatches'] == detail['actualSurfaceRefinementBatches'] == 8)
    no_surface = copy.deepcopy(enabled)
    no_surface['features'].pop('surface_refinement')
    tests.expect('herb_compatibility', 'herb gate does not implicitly enable roof additions', lambda:
                 len(botanical_rows) == 1043 and check(botanical_rows, no_surface)[0])

    # Invalid/off values do not authorize new identities; they leave old paths
    # intact, mirroring the existing independently gated roof contract.
    for flag in (None, False, 0, 1, 'true', 'false', {}, []):
        changed = copy.deepcopy(enabled)
        changed['features']['herb_planters'] = flag
        tests.expect('herb_feature_gate', 'new roster rejected under ' + repr(flag),
                     lambda changed=changed: check(rows, changed), False)
        tests.expect('herb_compatibility', 'old roster retained under ' + repr(flag),
                     lambda changed=changed: check(legacy_rows + roof_rows, changed))
    absent = copy.deepcopy(enabled)
    del absent['features']['herb_planters']
    tests.expect('herb_feature_gate', 'absent herb flag rejects replacement', lambda: check(rows, absent), False)
    tests.expect('herb_feature_gate', 'true herb flag rejects untouched legacy plants', lambda:
                 check(legacy_rows + roof_rows, enabled), False)
    for field in ('peer_culling_split', 'surface_refinement'):
        for flag in (None, False, 0, 1, 'true'):
            changed = copy.deepcopy(enabled)
            changed['features'][field] = flag
            tests.expect('herb_feature_gate', field + ' remains literal true: ' + repr(flag),
                         lambda changed=changed: check(rows, changed), False)

    for index, row in enumerate(rows):
        pair = c.key(row)
        if pair in ADDED:
            tests.expect('herb_adversarial', str(pair) + ' missing with recounted totals', lambda index=index:
                         check(rows[:index] + rows[index+1:], enabled), False)
            tests.expect('herb_adversarial', str(pair) + ' duplicate with recounted totals', lambda row=row:
                         check(rows + [row], enabled), False)
            variants = [('group', row['group'] + '/Cell_0_0'),
                        ('group', row['group'] + '_Far'),
                        ('group', row['group'] + '/Herbs'),
                        ('group', 'Shops/S09'),
                        ('material', row['material'] + 'Extra'),
                        ('material', 'Food')]
            if row['material'].startswith('HerbClay'):
                variants.append(('material', 'HerbClayUmber' if row['material'] == 'HerbClayOchre' else 'HerbClayOchre'))
            for field, value in variants:
                changed = dict(row, **{field: value})
                tests.expect('herb_adversarial', str(pair) + ' ' + field + '=' + value, lambda
                             index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:], enabled), False)
                tests.expect('herb_normalization', 'never canonicalize herb alias ' + str(c.key(changed)), lambda
                             changed=changed: c.canonical_key(*c.key(changed)) == c.key(changed))
        elif pair in protected:
            changed = dict(row, attributesAndIndicesSha256='f' * 64)
            tests.expect('herb_protected_payloads', str(pair) + ' still exact with herb flag', lambda
                         index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:], enabled), False)
    for pair in sorted(REMOVED):
        tests.expect('herb_adversarial', 'legacy plant batch cannot coexist: ' + str(pair), lambda pair=pair:
                     check(rows + [identity(pair)], enabled), False)
    for group, clay in SHOP_CLAY:
        wrong_clay = 'HerbClayUmber' if clay == 'HerbClayOchre' else 'HerbClayOchre'
        extra = dict(template, group=group, material=wrong_clay)
        tests.expect('herb_adversarial', group + ' cannot have both clay materials', lambda extra=extra:
                     check(rows + [extra], enabled), False)
    # Adding the new flag must not relax unrelated unprotected identities either.
    for index, row in enumerate(rows):
        if c.key(row) in protected | ADDED:
            continue
        changed = dict(row, group=row['group'] + '/Cell_0_0')
        tests.expect('herb_unrelated_roster', str(c.key(row)) + ' retains exact identity', lambda
                     index=index, changed=changed: check(rows[:index] + [changed] + rows[index+1:], enabled), False)
    for field in ('visualMeshCount', 'visualTriangles'):
        changed = counted_manifest(rows, enabled)
        changed[field] += 1
        tests.expect('herb_manifest', field + ' cannot be stale', lambda changed=changed:
                     c.validate_summaries(rows, changed, baseline), False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    from test_peer_culling_contract import Tests
    tests = Tests()
    data = args.root / 'Assets/TreeTopYokocho/Data'
    try:
        baseline = c.load_baseline(args.root)
        manifest = json.loads((data / 'WorldManifest.json').read_text())
        rows = [c.summarize(batch) for batch in c.read_visual(data / 'VisualMeshes.bytes')]
        tests.expect('actual_export', 'current export satisfies existing pinned contract', lambda:
                     c.validate_summaries(rows, manifest, baseline))
        run_roster_cases(rows, manifest, baseline, tests)
    except Exception as error:
        tests.failures.append(dict(test='suite setup', error=str(error), exception=type(error).__name__))
    print(json.dumps(dict(status='FAIL' if tests.failures else 'PASS', count=tests.count,
                         categories=tests.categories, failures=tests.failures,
                         scope='Read-only current export and recounted synthetic summary roster mutations; not an integrated herb geometry/Unity test'), indent=2))
    return bool(tests.failures)


if __name__ == '__main__':
    raise SystemExit(main())
