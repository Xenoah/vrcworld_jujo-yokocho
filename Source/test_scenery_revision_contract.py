"""Self-contained snow RGB/stage identity and preservation contract regressions.

All mixed-feature fixtures are SYNTHETIC SUMMARY fixtures, not generated worlds.
Every adversarial roster has recounted totals, so count drift cannot hide a gap.
Actual native array mutations are separately labeled. Optional --snow-candidate
accepts a reviewed isolated native snow fixture for prospective after-RGB tests.
No baseline writes, full-world generation, Blender, or Unity work occurs here.
"""
import argparse
import copy
import hashlib
import itertools
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
import numpy as np
import peer_culling_contract as c

# Independent literal oracle, never inferred from production allowlists.
PEER_PIN = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
STAGE_PIN = '6f93f57172d2b6dbe71e49c2b75de0a910805f109fdfe09e93456f7570e81e2c'
STAGE_ADDED = {
    ('Stage/Noh/RoofDetail/Courses', 'Kawara'),
    ('Stage/Noh/RoofDetail/Caps', 'Kawara'),
    ('Stage/Noh/RoofDetail/Joinery', 'StageCypress'),
    ('Stage/Noh/RoofDetail/Joinery', 'DarkTimber'),
}
# Independent reviewed final native summaries for the four stable additions.
# Synthetic stage-on combinations always use these exact approved summaries.
STAGE_APPROVED = {
    ('Stage/Noh/RoofDetail/Courses', 'Kawara'): dict(
        vertices=34944, triangles=21904,
        geometrySha256='b0b44cf78739cf6e806bcc2dd753e68bc0f72e8002b9828f5d9c4bd73dce6bf4',
        attributesAndIndicesSha256='9c44deeb8195c430346986194cc9f32cde16b6cf67a11b236d4f4a810666b400'),
    ('Stage/Noh/RoofDetail/Caps', 'Kawara'): dict(
        vertices=3444, triangles=2132,
        geometrySha256='f0dae0231b33d8c6e6a5a81c83d1f8f65cd6c0c09e5375f5d2ffd22c5670054c',
        attributesAndIndicesSha256='c5a357b8b85fa58fc1c789c109ef48b5cd0797bcf6a249e9a8234953671ef54f'),
    ('Stage/Noh/RoofDetail/Joinery', 'DarkTimber'): dict(
        vertices=448, triangles=480,
        geometrySha256='d58f33c32bc2d65dde4a1d548c734b30fabedbf8fa283d4394d241ba13fa4937',
        attributesAndIndicesSha256='13eeefa5b287f041e7f414291f0502e3619c0953e2908c95a069eddfce046fcc'),
    ('Stage/Noh/RoofDetail/Joinery', 'StageCypress'): dict(
        vertices=1056, triangles=496,
        geometrySha256='b1747df562bb944ce60e5139d26c1b2cfeb7d7e2b83a52fb11d863e357437e84',
        attributesAndIndicesSha256='ac1dd6ea8f5e5fc456730280036068848b886ba27350012404ee7889eea8fdff'),
}
SNOW_HASHES = {
    ('Landscape/SnowRange_0', 'AlpineSnow'): ('41fc6db1aba35e1d7dfa94d0aff85d73b9074e23c05ee8650fd485dcee3e8618', '78d932fa17182d8796aa176ca091924ab7425c8b707311a4983998abdc1d06db'),
    ('Landscape/SnowRange_0', 'AlpineSnowShade'): ('de0784b4acd480c95f560e5887510cd431627796cd92b54e10267ced84c47656', '54dc6ef6dde6cfe62add9021d3667f333daeffa4b3a7e01707244ec92f64fde7'),
    ('Landscape/SnowRange_1', 'AlpineSnow'): ('0f8b11c81bb07ea863ae1c5757c861000d5b657d2dcfef3a22da644202d699f9', '955a599ebc5f64999266b94d0d239b36c889a1ea610e14ff12aded27fe41c821'),
    ('Landscape/SnowRange_1', 'AlpineSnowShade'): ('2e30bc645036ed2264c4b56ca929d0d71251de7a0d7250695396f8da38315a17', 'a31d8b056968ea5a132c6d0f27004f8dd92ceefb42af167cd5439698cd7c2825'),
    ('Landscape/SnowRange_2', 'AlpineSnow'): ('63645107cf505f488cf26cd0633e41f9b7a6a0c9281d386f1233c196327af4ec', '83f41635fc969571b67f33e6e07f3cff4177aeefaa6669bf56b888bac821fa6a'),
    ('Landscape/SnowRange_2', 'AlpineSnowShade'): ('9261f575f655f37699ba9f2fb33e605f7cd837ffdaaecb3d7835414c5ace8026', 'cd409e7e28b21de58166ecb2f900c83d5a98790567b1a5554d5b33cabe929662'),
    ('Landscape/SnowRange_3', 'AlpineSnow'): ('3c2947b696f27c94dd5e0c2e353b0c93d1cae3410a156638a76cdf48731ec565', '7d61d1bd83d2ba474d884e84f4f07eddbfb05fd7427b6bea1ad042a268ba4460'),
    ('Landscape/SnowRange_3', 'AlpineSnowShade'): ('81156765e75251ad1432f07d495a59b68d312f792e3eb52e62fb630839d890be', '255678dcf69988b03a7bb0fc210005a330c4611b28c105f2948c98a43e5f4f69'),
}
STAGE_ORIGINAL = {
    ('Stage/Noh/Floor', 'Bronze'), ('Stage/Noh/Floor', 'DarkTimber'),
    ('Stage/Noh/Floor', 'StageCypress'), ('Stage/Noh/HipRoof', 'DarkTimber'),
    ('Stage/Noh/HipRoof', 'Kawara'), ('Stage/Noh/HipRoof', 'StageCypress'),
    ('Stage/Noh/Lighting', 'Bronze'), ('Stage/Noh/Lighting', 'Iron'),
    ('Stage/Noh/Lighting', 'PaperLight'), ('Stage/Noh/PineCrest', 'Bronze'),
    ('Stage/Noh/PineCrest', 'DarkTimber'), ('Stage/Noh/Posts', 'Bronze'),
    ('Stage/Noh/Posts', 'StageCypress'), ('Stage/Noh/Support', 'Cedar'),
    ('Stage/Noh/Support', 'DarkTimber'),
}
FALSE_FLAGS = (None, False, 0, 1, 1.0, 'true', 'True', 'false', {}, [], np.bool_(True))


def counted(rows, manifest):
    result = dict(manifest)
    result['visualMeshCount'] = len(rows)
    result['visualTriangles'] = sum(row['triangles'] for row in rows)
    return result


def run_scenery_cases(current_rows, current_manifest, baseline, tests, *, batches=None,
                      root=None, snow_candidate_batches=None):
    """Both pre/post-integration exports work; synthetic fixtures are explicit."""
    baseline_before = copy.deepcopy(baseline)
    protected = ({c.key(row) for row in baseline['protectedGroups']} - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
    old = {c.key(row): row for row in baseline['protectedGroups']}
    current = {c.key(row): row for row in current_rows}
    template = next(row for row in current_rows if c.key(row) not in protected | STAGE_ORIGINAL)
    check = lambda rows, manifest, b=baseline: c.validate_summaries(rows, counted(rows, manifest), b)
    tests.expect('scenery_pinning', 'exact eight independent before/after hashes', lambda:
                 len(c.SNOW_DEPOSITION_REVISIONS) == 8 and
                 {(g, m): (before, after) for g, m, before, after in c.SNOW_DEPOSITION_REVISIONS} == SNOW_HASHES)
    tests.expect('scenery_pinning', 'exact four independent new stage identities', lambda:
                 len(c.STAGE_ROOF_CRAFT_BATCHES) == 4 and set(c.STAGE_ROOF_CRAFT_BATCHES) == STAGE_ADDED)
    tests.expect('scenery_pinning', 'exact independent four final stage payload pins', lambda:
                 len(c.STAGE_ROOF_CRAFT_PAYLOADS) == 4 and
                 {(g,m): dict(vertices=nv,triangles=nt,geometrySha256=geo,attributesAndIndicesSha256=attr)
                  for g,m,nv,nt,geo,attr in c.STAGE_ROOF_CRAFT_PAYLOADS} == STAGE_APPROVED)
    tests.expect('scenery_pinning', '15 original stage pins are additional to original 603', lambda:
                 len(c.STAGE_ORIGINAL_PAYLOADS) == 15 and
                 {(r[0], r[1]) for r in c.STAGE_ORIGINAL_PAYLOADS} == STAGE_ORIGINAL and
                 not STAGE_ORIGINAL & protected and set(SNOW_HASHES) <= protected)
    tests.expect('scenery_pinning', 'fixed baseline source constants', lambda:
                 c.BASELINE_FILE_SHA256 == PEER_PIN and c.STAGE_BASELINE_FILE_SHA256 == STAGE_PIN)
    if root is not None:
        tests.expect('scenery_pinning', 'peer file SHA independently fixed', lambda:
                     hashlib.sha256((root / 'Docs/baselines' / c.BASELINE_NAME).read_bytes()).hexdigest() == PEER_PIN)
        tests.expect('scenery_pinning', 'separate original-stage archive baseline fixed', lambda:
                     hashlib.sha256((root / 'Docs/baselines' / c.STAGE_BASELINE_NAME).read_bytes()).hexdigest() == STAGE_PIN)
        tests.expect('scenery_pinning', 'stage code payloads exactly match frozen archive file', lambda:
                     len(c.load_stage_baseline(root)['originalStageGroups']) == 15)

    # Fixture starts at the frozen peer roster, uses actual stage/other protected
    # rows, and only synthesizes absent unprotected legacy/replacement identities.
    roster = protected | {tuple(pair) for pair in baseline['unprotectedBatchKeys']}
    base = []
    for pair in sorted(roster):
        row = dict(current.get(pair, dict(template, group=pair[0], material=pair[1])))
        if pair in SNOW_HASHES:
            row = dict(old[pair])  # immutable baseline attributes, never future colors
        base.append(row)
    from test_herb_planter_roster_contract import ADDED as HERBS, REMOVED as PLANTS, ROOFS
    def fixture(surface=False, herbs=False, snow=False, stage=False):
        rows = [dict(row) for row in base if not herbs or c.key(row) not in PLANTS]
        added = (ROOFS if surface else set()) | (HERBS if herbs else set()) | (STAGE_ADDED if stage else set())
        rows += [dict(group=pair[0], material=pair[1], **STAGE_APPROVED[pair])
                 if pair in STAGE_APPROVED else
                 dict(current.get(pair, dict(template, group=pair[0], material=pair[1]))) for pair in sorted(added)]
        if snow:
            rows = [dict(row, attributesAndIndicesSha256=SNOW_HASHES[c.key(row)][1])
                    if c.key(row) in SNOW_HASHES else row for row in rows]
        manifest = copy.deepcopy(current_manifest)
        manifest['features'] = dict(manifest.get('features', {}), peer_culling_split=True,
                                    surface_refinement=surface, herb_planters=herbs,
                                    snow_deposition=snow, stage_roof_craft=stage)
        return rows, manifest

    # Keep the caller's current exact cloud state; cloud revisions remove eight
    # old-geometry payloads and eight unchanged-attribute payloads independently
    # of snow. This historical four-feature matrix remains valid after cloud integration.
    cloud = current_manifest.get('features', {}).get('cloud_depth') is True
    for surface, herbs, snow, stage in itertools.product((False, True), repeat=4):
        rows, manifest = fixture(surface, herbs, snow, stage)
        ok, detail = check(rows, manifest)
        tests.expect('scenery_synthetic_matrix', repr((surface, herbs, snow, stage)), lambda:
                     ok and detail['expectedTotalBatches'] == detail['actualTotalBatches'] == 1051 + 8*surface - 8*herbs + 4*stage
                     and detail['expectedProtectedBatches'] == detail['actualProtectedBatches'] == 603
                     and detail['unchangedProtectedBatches'] == 595 - 8*int(snow) - 8*int(cloud)
                     and detail['unchangedProtectedGeometryBatches'] == 595 - 8*int(cloud)
                     and detail['geometryRevisedProtectedBatches'] == 8*int(cloud)
                     and detail['colorRevisedProtectedBatches'] == (8 if snow else 0)
                     and detail['exactPeerSplitProtectedBatches'] == 8
                     and detail['actualSnowDepositionBatches'] == (8 if snow else 0)
                     and detail['actualStageRoofCraftBatches'] == (4 if stage else 0)
                     and detail['separatelyPinnedOriginalStageBatches'] == (15 if stage else 0)
                     and detail['separatelyPinnedStageRoofCraftBatches'] == (4 if stage else 0)
                     and detail['exactStageRoofCraftPayloadBatches'] == (4 if stage else 0))

    rows, manifest = fixture(True, True, True, True)
    lookup = {c.key(row): i for i, row in enumerate(rows)}
    for feature in ('snow_deposition', 'stage_roof_craft'):
        for flag in FALSE_FLAGS:
            changed = copy.deepcopy(manifest); changed['features'][feature] = flag
            tests.expect('scenery_literal_gates', feature + ' rejects candidate under ' + repr(flag),
                         lambda changed=changed: check(rows, changed), False)
            reverted, _ = fixture(True, True, feature != 'snow_deposition', feature != 'stage_roof_craft')
            tests.expect('scenery_legacy_gates', feature + ' leaves legacy path under ' + repr(flag),
                         lambda reverted=reverted, changed=changed: check(reverted, changed))
        changed = copy.deepcopy(manifest); del changed['features'][feature]
        tests.expect('scenery_literal_gates', feature + ' absent rejects candidate', lambda: check(rows, changed), False)
        reverted, _ = fixture(True, True, feature != 'snow_deposition', feature != 'stage_roof_craft')
        tests.expect('scenery_literal_gates', feature + ' true requires complete revision', lambda: check(reverted, manifest), False)
    for feature in ('peer_culling_split', 'surface_refinement', 'herb_planters'):
        for flag in FALSE_FLAGS:
            changed = copy.deepcopy(manifest); changed['features'][feature] = flag
            tests.expect('scenery_preserves_legacy_gates', feature + ' unchanged gate ' + repr(flag),
                         lambda changed=changed: check(rows, changed), False)

    for pair in sorted(set(SNOW_HASHES) | STAGE_ADDED | STAGE_ORIGINAL):
        index = lookup[pair]; row = rows[index]
        tests.expect('scenery_exact_roster', str(pair) + ' missing', lambda index=index:
                     check(rows[:index]+rows[index+1:], manifest), False)
        tests.expect('scenery_exact_roster', str(pair) + ' duplicate', lambda row=row:
                     check(rows+[row], manifest), False)
        for field, value in [('group', row['group'] + '/Cell_0_0'), ('group', row['group'] + '_Far'),
                             ('group', row['group'] + '/Extra'), ('material', row['material'] + 'Extra')]:
            changed = dict(row, **{field: value})
            tests.expect('scenery_aliases', str(pair) + ' rejects ' + str(c.key(changed)), lambda index=index, changed=changed:
                         check(rows[:index]+[changed]+rows[index+1:], manifest), False)
            tests.expect('scenery_aliases', 'does not canonicalize ' + str(c.key(changed)), lambda changed=changed:
                         c.canonical_key(*c.key(changed)) == c.key(changed))
        for field in ('geometrySha256', 'attributesAndIndicesSha256'):
            for value in (None, '', '0'*64, 'f'*64):
                changed = dict(row, **{field: value})
                tests.expect('scenery_exact_payload', str(pair) + ' wrong ' + field + ' ' + repr(value), lambda index=index, changed=changed:
                             check(rows[:index]+[changed]+rows[index+1:], manifest), False)
            changed = dict(row); del changed[field]
            tests.expect('scenery_exact_payload', str(pair) + ' missing ' + field, lambda index=index, changed=changed:
                         check(rows[:index]+[changed]+rows[index+1:], manifest), False)
        for field in ('vertices', 'triangles'):
            changed = dict(row, **{field: row[field]+1})
            tests.expect('scenery_exact_payload', str(pair) + ' changed ' + field, lambda index=index, changed=changed:
                         check(rows[:index]+[changed]+rows[index+1:], manifest), False)
        if pair in SNOW_HASHES:
            changed = dict(row, attributesAndIndicesSha256=SNOW_HASHES[pair][0])
            tests.expect('snow_before_after', str(pair) + ' before color forbidden under true', lambda index=index, changed=changed:
                         check(rows[:index]+[changed]+rows[index+1:], manifest), False)
            for value in (None, '0'*64, SNOW_HASHES[pair][1]):
                altered_baseline = copy.deepcopy(baseline)
                target = next(r for r in altered_baseline['protectedGroups'] if c.key(r) == pair)
                if value is None: del target['attributesAndIndicesSha256']
                else: target['attributesAndIndicesSha256'] = value
                tests.expect('snow_before_pinning', str(pair) + ' missing/wrong/replaced baseline before pin', lambda altered_baseline=altered_baseline:
                             check(rows, manifest, altered_baseline), False)
    # New detail payload negatives require their specific admission reason,
    # independently of all identity/manifest errors.
    for pair in sorted(STAGE_ADDED):
        index = lookup[pair]
        for field in ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256'):
            changed = dict(rows[index])
            changed[field] = changed[field]+1 if field in ('vertices', 'triangles') else '0'*64
            invalid = rows[:index]+[changed]+rows[index+1:]
            def exact_stage_rejection(invalid=invalid, pair=pair):
                ok, detail = check(invalid, manifest)
                return not ok and any(error.get('reason') == 'Approved stage-roof detail payload changed'
                                      and tuple(error.get('key', ())) == pair for error in detail['errors'])
            tests.expect('stage_payload_enforcement', str(pair)+' '+field+' fails at exact stage pin',
                         exact_stage_rejection)
    for pair in [('Stage/Unknown', 'Kawara'), ('Stage/Noh/RoofDetail/Unknown', 'Kawara'),
                 ('Stage/Noh/RoofDetail/Courses', 'DarkTimber'), ('Stage/Noh/RoofDetail/Caps', 'StageCypress'),
                 ('Landscape/SnowRange_4', 'AlpineSnow'), ('Landscape/SnowRange_0', 'AlpineSnowExtra')]:
        extra = dict(template, group=pair[0], material=pair[1])
        tests.expect('scenery_extra_groups', str(pair) + ' cannot use group prefix exemption', lambda extra=extra:
                     check(rows+[extra], manifest), False)
    for pair in sorted(protected - set(SNOW_HASHES)):
        index = lookup[pair]; changed = dict(rows[index], attributesAndIndicesSha256='0'*64)
        tests.expect('scenery_other_protected', str(pair) + ' unchanged under both new gates', lambda index=index, changed=changed:
                     check(rows[:index]+[changed]+rows[index+1:], manifest), False)

    # Actual array tests admit the unmutated array first, then independently alter
    # immutable fields. This prevents a stale-color rejection from masquerading
    # as a position/UV/index/alpha rejection in prospective synthetic summaries.
    def array_cases(payloads, after):
        fixture_rows, fixture_manifest = fixture(True, True, after, True)
        indices = {c.key(row): i for i, row in enumerate(fixture_rows)}
        selected = [batch for batch in payloads if c.key(batch) in set(SNOW_HASHES) | STAGE_ORIGINAL | STAGE_ADDED]
        for original in selected:
            pair = c.key(original); index = indices[pair]
            combined = fixture_rows[:index]+[c.summarize(original)]+fixture_rows[index+1:]
            category = 'snow_actual_after_arrays' if pair in SNOW_HASHES and after else 'scenery_actual_native_arrays'
            tests.expect(category, str(pair) + ' exact unmodified payload admitted', lambda combined=combined:
                         check(combined, fixture_manifest))
            for mutation in ('position_ulp', 'uv_ulp', 'rgb_bit', 'alpha_bit', 'winding', 'index', 'duplicate_triangle', 'extra_vertex'):
                changed = dict(original, **{field: original[field].copy() for field in ('vertices','uv','colors','faces')})
                vertex = int(changed['faces'][0, 0])
                if mutation in ('position_ulp', 'uv_ulp'):
                    field = 'vertices' if mutation == 'position_ulp' else 'uv'
                    changed[field][vertex, 0] = np.nextafter(changed[field][vertex, 0], np.float32(np.inf))
                elif mutation in ('rgb_bit', 'alpha_bit'):
                    changed['colors'][vertex, 3 if mutation == 'alpha_bit' else 0] ^= 1
                elif mutation == 'winding': changed['faces'][0] = changed['faces'][0, [0,2,1]]
                elif mutation == 'index': changed['faces'][0, 0] = (vertex+1) % len(changed['vertices'])
                elif mutation == 'duplicate_triangle': changed['faces'] = np.concatenate([changed['faces'],changed['faces'][:1]])
                else:
                    for field in ('vertices','uv','colors'):
                        changed[field] = np.concatenate([changed[field],changed[field][vertex:vertex+1]])
                combined = fixture_rows[:index]+[c.summarize(changed)]+fixture_rows[index+1:]
                tests.expect(category, str(pair) + ' reject ' + mutation, lambda combined=combined:
                             check(combined, fixture_manifest), False)
    if batches:
        array_cases(batches, current_manifest.get('features', {}).get('snow_deposition') is True)
    if snow_candidate_batches:
        tests.expect('snow_actual_after_arrays', 'isolated candidate provides all exact eight snow identities', lambda:
                     {c.key(b) for b in snow_candidate_batches if c.key(b) in SNOW_HASHES} == set(SNOW_HASHES))
        array_cases(snow_candidate_batches, True)

    if root is not None:
        raw_reader = Path.read_bytes
        _, true_manifest = fixture(True, True, True, True)
        for name in (c.BASELINE_NAME, c.STAGE_BASELINE_NAME):
            def corrupt(path, name=name):
                raw = raw_reader(path)
                return raw+b' ' if path.name == name else raw
            with patch.object(Path, 'read_bytes', corrupt):
                def rejects_changed_pin():
                    ok, detail = c.validate_peer_culling(root, counted(rows, true_manifest))
                    expected_error = ('Frozen v2.8 peer baseline file hash changed' if name == c.BASELINE_NAME
                                      else 'Frozen v2.10 original-stage baseline file hash changed')
                    return not ok and detail.get('error') == expected_error
                tests.expect('scenery_baseline_bytes', name + ' whitespace tamper fails specifically at pin admission',
                             rejects_changed_pin)
            def missing(path, name=name):
                if path.name == name: raise FileNotFoundError(name)
                return raw_reader(path)
            with patch.object(Path, 'read_bytes', missing):
                def rejects_missing_pin():
                    ok, detail = c.validate_peer_culling(root, counted(rows, true_manifest))
                    return not ok and detail.get('error') == name
                tests.expect('scenery_baseline_bytes', name + ' missing fails specifically at pin admission',
                             rejects_missing_pin)
    for field in ('visualMeshCount', 'visualTriangles'):
        changed = counted(rows, manifest); changed[field] += 1
        tests.expect('scenery_manifest', field + ' remains strict', lambda changed=changed:
                     c.validate_summaries(rows, changed, baseline), False)
    tests.expect('scenery_pinning', 'validation never rewrites/mutates peer baseline object', lambda:
                 baseline == baseline_before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--snow-candidate', type=Path)
    args = parser.parse_args()
    from test_peer_culling_contract import Tests
    tests = Tests()
    try:
        baseline = c.load_baseline(args.root)
        data = args.root/'Assets/TreeTopYokocho/Data'
        manifest = json.loads((data/'WorldManifest.json').read_text())
        batches = c.read_visual(data/'VisualMeshes.bytes')
        rows = [c.summarize(batch) for batch in batches]
        tests.expect('actual_export', 'only current exported bytes admitted as actual export', lambda:
                     c.validate_peer_culling(args.root, manifest))
        run_scenery_cases(rows, manifest, baseline, tests, batches=batches, root=args.root,
                          snow_candidate_batches=c.read_visual(args.snow_candidate) if args.snow_candidate else None)
    except Exception as error:
        tests.failures.append(dict(test='suite setup', error=str(error), exception=type(error).__name__))
    print(json.dumps(dict(status='FAIL' if tests.failures else 'PASS', count=tests.count,
                         categories=tests.categories, failures=tests.failures,
                         scope='Actual current native arrays plus explicitly synthetic mixed-feature summaries; optional actual isolated snow candidate; no future full-world export/Blender/Unity claim'), indent=2))
    return bool(tests.failures)


if __name__ == '__main__':
    raise SystemExit(main())
