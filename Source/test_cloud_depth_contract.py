"""Self-contained exact cloud Z-revision contract and adversarial regressions.

Feature combinations are SYNTHETIC SUMMARY fixtures, not generated worlds.
Real current-native arrays are tested under their current literal cloud flag.
Optional --cloud-candidate is an isolated after fixture inserted into synthetic
summaries; it is NOT evidence that a future integrated cloud world passed.
No generation, rendering, baseline writes, network, or production transforms.
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

PEER_PIN = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
STAGE_PIN = '6f93f57172d2b6dbe71e49c2b75de0a910805f109fdfe09e93456f7570e81e2c'
CLOUD_CANDIDATE_PIN = '0755cb8c239bab3a96c09ae6724414dba35e2d4eebd9034618c3179421503612'
# Independent literal oracle: does not derive expectations from the validator,
# read a proposal at runtime, or compute after data from native-float32 Z.
BEFORE = {('Landscape/CloudSea_Near_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '3ed9b7861849c3a2b98aace773ef719429c75ca54caba692da6d24c331fd7804',
                                                    'attributesAndIndicesSha256': '39533559fe10ceea7b430cf9a7bfe8c5b70f13cf658ff584906c01ecdeeaef30'},
 ('Landscape/CloudSea_Near_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '46d94503497325c5ea4cc5cf79d3ba92a08e46e031710960c3ead478b94c6b8e',
                                                    'attributesAndIndicesSha256': '174931185601eb5e324e628d01af77c0dfb7ff50f59732bf096661a3142e12be'},
 ('Landscape/CloudSea_Near_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': 'daa45ed940a0e36ef256681b0a8572c86d814e2b06398a3deb620719cbdaf579',
                                                    'attributesAndIndicesSha256': '8a24940b02540daafcaa6ed6775463cddad807fd258706cd6be8aff81083b123'},
 ('Landscape/CloudSea_Near_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': 'c2490b2025c0aa5eecf298420ed3860b24e54f107a8e7f4965e3cbcbefd7d048',
                                                    'attributesAndIndicesSha256': '9bf0bbc206865d717693d1da5f92ad23144dfd76bd95ab79d155c5c74e2aa59e'},
 ('Landscape/CloudSea_Far_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': '064b002f169e9c74a443b2814061a4e4318f8e40759e114a5918ad050abcc903',
                                                   'attributesAndIndicesSha256': '1e002e29019330aa4a436d0785c9e017dc22cc794ef4c4f97fcb6d77c1330530'},
 ('Landscape/CloudSea_Far_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': '0c21786caa3cd19e975db07ee4d822e5287e4d0381abc164640b56fac2af2058',
                                                   'attributesAndIndicesSha256': 'ebea8081e313aa451c23f98682eaa36f1ef909fc258c3983fa1748e479055745'},
 ('Landscape/CloudSea_Far_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': 'fb07f9b4407f8e342c8c0e3c906115e4fe5105c010edebfde64754e723c5a102',
                                                   'attributesAndIndicesSha256': '9bfdd02a508d94559410c5c4a18c54490735566d4c2d1ab56fdf5b9f7c9f551e'},
 ('Landscape/CloudSea_Far_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': '30fdb909b53a6c556c0c0e57cbd196ab1df41712c3d731b1e88c9a41947b1b19',
                                                   'attributesAndIndicesSha256': '1066eddde531ee7d1ce0e0d0bbf95d53ca68adb9456aa4f096262e7121d0affe'}}
AFTER = {('Landscape/CloudSea_Near_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '97006ec2205d260f92d1426386f3732e17799d63fb28883fb518ba25fea5cd30',
                                                    'attributesAndIndicesSha256': '192c639efd14684157a634527fc2029d190dc76b479b87da17e9c94cfdd0cb2c'},
 ('Landscape/CloudSea_Near_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '1187b789653e92bcc423626d95b34f02ce32c36197ee8ffe4755e944012c7bba',
                                                    'attributesAndIndicesSha256': '0d2bed6a4cbcfd6dbf0c512724650234506d54bc6971cd3e3921599e4cac2f6d'},
 ('Landscape/CloudSea_Near_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': 'c410e6dcab05841783685dca8d545a84cbff90aade9cb43d27ad287b8df23a09',
                                                    'attributesAndIndicesSha256': '3f65d7b9cddc906f2f762cdb9775599d44944ea7c1bf339cf6a3fbbdda7366b5'},
 ('Landscape/CloudSea_Near_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': '9997de3a3814b86b2b24aac6ae1c46b6a9df3d84cf3e727c388b2cc28cd11379',
                                                    'attributesAndIndicesSha256': '30df1cf7353beb68886f0acb563a3ae819146bad2f231c466e3c3ac4edc7c2bc'},
 ('Landscape/CloudSea_Far_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': '40da297159ab0045dc60c5cf0229a23ff325132679fbfec5fcdbb7f6eb1d8a9f',
                                                   'attributesAndIndicesSha256': '1ca464e0853e9f1c7e259822380ba00e63ce808841293428cee47521ea4ab62b'},
 ('Landscape/CloudSea_Far_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': '99eeb4951945d559111b05b7334629fffc7d755bca27c9ec4043b5e07bb58267',
                                                   'attributesAndIndicesSha256': '9a2595032e5a1d6f0d58d29d2a1510ebeb48b7d51c04cd206b3d2f387337411c'},
 ('Landscape/CloudSea_Far_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': '9c2656172ea19f809e6877c19817269f2a98ca8d73fbebce636eae1faed55743',
                                                   'attributesAndIndicesSha256': '01271b20d6ed0d3c520441e248e07d1c17b40346f32febec4cb5cc31f67a9798'},
 ('Landscape/CloudSea_Far_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': '4a5d45d82158d00cffd21a97ed276d1f1c7ecba6886aa1ea9af51fa509a79961',
                                                   'attributesAndIndicesSha256': '99d15f1aa5540b08a8f692a9fc0836f0c13e1479382f1e929abbd82d51818ba2'}}
# Explicitly FORBIDDEN native-float32 illustration, pinned independently of
# production approved after hashes. Similar coordinates are never sufficient.
ILLUSTRATION = {('Landscape/CloudSea_Near_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '57f6a508a0fe394b2e57b6ebf05b5a38942adb61c1cb239e389efd3994b11578',
                                                    'attributesAndIndicesSha256': '910568e6b454b5487bed6b7cc8ebb85fed26296fc9921838326bea62057a9280'},
 ('Landscape/CloudSea_Near_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_NE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 2916,
                                                    'triangles': 5184,
                                                    'geometrySha256': '9d0097d544730cdc50f1dd4c7b44c3db99e7a291dd6ad70e077b8dd65f77b209',
                                                    'attributesAndIndicesSha256': '02dd00313a06785a261c04ab1d8bbe9bb9543b0e3a3a58a4c80368fb1b79bb5e'},
 ('Landscape/CloudSea_Near_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SW',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': '56e7481814089cb14f5478d014554dc83ae3ece6c065fef514690d2303a2e42a',
                                                    'attributesAndIndicesSha256': '6aac68c9bf9867096c8615139b7cc0e7d81d3cc15ad1f08e94790bff579d2e12'},
 ('Landscape/CloudSea_Near_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Near_SE',
                                                    'material': 'CloudSeaSilver',
                                                    'vertices': 1458,
                                                    'triangles': 2592,
                                                    'geometrySha256': '8850afeba79797e0ce5e1dbd85eba92f2fbfefbfd0c811243f342ca023b94ec4',
                                                    'attributesAndIndicesSha256': 'fd2ce6f6d74e85e0e6a3d3482fd6858b8659b6490288179b333d147f09d95f3d'},
 ('Landscape/CloudSea_Far_NW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': '0dec28e6cb1184a327c8ac122cdf9ed32690f357dc6e752853a4b2844079cdf0',
                                                   'attributesAndIndicesSha256': '74b04208c3366ac931601234c3f06ac6ef269abd73167548442d8de3f86196ce'},
 ('Landscape/CloudSea_Far_NE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_NE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 3645,
                                                   'triangles': 6480,
                                                   'geometrySha256': 'de539134dbcaa2255446859dbdb813750a8b80d8aa501ddc94b1203fae835a2e',
                                                   'attributesAndIndicesSha256': 'b378f2aeec7f0fdfe2e22fdb06f135e9eac940b1cd2fea27f64268ce54aef7ac'},
 ('Landscape/CloudSea_Far_SW', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SW',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': '39b38a4dda8adc48e1fd826f45ecdc8cde0982618eb098a28586c5f458e530fc',
                                                   'attributesAndIndicesSha256': '82ef00d08092b089f1a0a206f608d63d122f9af1a9ff7d1e2f5b40de5c4422fd'},
 ('Landscape/CloudSea_Far_SE', 'CloudSeaSilver'): {'group': 'Landscape/CloudSea_Far_SE',
                                                   'material': 'CloudSeaSilver',
                                                   'vertices': 2187,
                                                   'triangles': 3888,
                                                   'geometrySha256': 'fd36dad6988b71375f9f475402c8d2f06fb2a4e54e5d8fc833c75e7294c9f4c8',
                                                   'attributesAndIndicesSha256': 'cb724d0513603fe25a6f4f72fb7bece2082d01b9511c5f038247cea255a515a3'}}
FALSE_FLAGS = (None, False, 0, 1, 1.0, 'true', 'True', 'false', {}, [], np.bool_(True))
FIELDS = ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256')


def counted(rows, manifest):
    result = dict(manifest)
    result['visualMeshCount'] = len(rows)
    result['visualTriangles'] = sum(row['triangles'] for row in rows)
    return result


def rejects(result, reasons, pair=None):
    """A negative passes only for precisely the intended diagnostics."""
    ok, detail = result
    errors = detail.get('errors', [])
    return (not ok and bool(errors) and {e.get('reason') for e in errors} == set(reasons)
            and (pair is None or any(e.get('key') == pair or pair in e.get('keys', []) for e in errors)))


def run_cloud_cases(current_rows, current_manifest, baseline, tests, *, batches=None,
                    root=None, cloud_candidate_batches=None):
    """Current native input may be before or after; summaries are labeled synthetic."""
    # This older matrix stays explicitly historical for Identity. The dedicated
    # noren suite exercises the independent full64 matrix and all native payloads.
    if isinstance(current_manifest.get('features'), dict) and current_manifest['features'].get('noren_craft') is True:
        from test_noren_payload_contract import historical_identity_fixture
        current_rows, current_manifest = historical_identity_fixture(current_rows, current_manifest)
    from test_scenery_revision_contract import SNOW_HASHES, STAGE_ADDED, STAGE_ORIGINAL, STAGE_APPROVED
    from test_herb_planter_roster_contract import ADDED as HERBS, REMOVED as PLANTS, ROOFS
    baseline_before = copy.deepcopy(baseline)
    old = {c.key(row): row for row in baseline['protectedGroups']}
    protected = (set(old) - set(c.OLD_KEYS)) | set(c.NEW_TO_OLD)
    current = {c.key(row): row for row in current_rows}
    template = next(row for row in current_rows if c.key(row) not in protected | STAGE_ORIGINAL)
    check = lambda rows, manifest, b=baseline: c.validate_summaries(rows, counted(rows, manifest), b)
    expected_constants = {
        pair: tuple(BEFORE[pair][field] for field in FIELDS) +
        (AFTER[pair]['geometrySha256'], AFTER[pair]['attributesAndIndicesSha256']) for pair in BEFORE
    }
    tests.expect('cloud_independent_pins', 'exact eight independent identity/count/before/after pins', lambda:
                 len(c.CLOUD_DEPTH_REVISIONS) == 8 and
                 {(r[0], r[1]): tuple(r[2:]) for r in c.CLOUD_DEPTH_REVISIONS} == expected_constants)
    tests.expect('cloud_independent_pins', 'all before summaries exactly match immutable existing peer baseline', lambda:
                 all(all(old.get(pair, {}).get(field) == value for field, value in row.items())
                     for pair, row in BEFORE.items()))
    tests.expect('cloud_independent_pins', 'fixed counts and hashes change only eight explicit old protected entries', lambda:
                 set(BEFORE) == set(AFTER) and len(BEFORE) == 8 and set(BEFORE) <= protected
                 and not set(BEFORE) & (set(SNOW_HASHES) | STAGE_ORIGINAL | STAGE_ADDED)
                 and sum(r['vertices'] for r in BEFORE.values()) == 20412
                 and sum(r['triangles'] for r in BEFORE.values()) == 36288
                 and all(BEFORE[k]['vertices'] == AFTER[k]['vertices']
                         and BEFORE[k]['triangles'] == AFTER[k]['triangles'] for k in BEFORE))
    tests.expect('cloud_independent_pins', 'peer and separate original-stage baseline constants unchanged', lambda:
                 c.BASELINE_FILE_SHA256 == PEER_PIN and c.STAGE_BASELINE_FILE_SHA256 == STAGE_PIN)
    if root is not None:
        for name, pin in ((c.BASELINE_NAME, PEER_PIN), (c.STAGE_BASELINE_NAME, STAGE_PIN)):
            tests.expect('cloud_independent_pins', name + ' bytes unchanged', lambda name=name, pin=pin:
                         hashlib.sha256((root/'Docs/baselines'/name).read_bytes()).hexdigest() == pin)

    roster = protected | {tuple(pair) for pair in baseline['unprotectedBatchKeys']}
    base = []
    for pair in sorted(roster):
        row = dict(current.get(pair, dict(template, group=pair[0], material=pair[1])))
        if pair in BEFORE or pair in SNOW_HASHES:
            row = dict(old[pair])
        base.append(row)

    def fixture(surface=False, herbs=False, snow=False, stage=False, cloud=False):
        rows = [dict(row) for row in base if not herbs or c.key(row) not in PLANTS]
        added = (ROOFS if surface else set()) | (HERBS if herbs else set()) | (STAGE_ADDED if stage else set())
        rows += [dict(group=pair[0], material=pair[1], **STAGE_APPROVED[pair])
                 if pair in STAGE_APPROVED else
                 dict(current.get(pair, dict(template, group=pair[0], material=pair[1]))) for pair in sorted(added)]
        for i, row in enumerate(rows):
            pair = c.key(row)
            if snow and pair in SNOW_HASHES:
                rows[i] = dict(row, attributesAndIndicesSha256=SNOW_HASHES[pair][1])
            if cloud and pair in AFTER:
                rows[i] = dict(AFTER[pair])
        manifest = copy.deepcopy(current_manifest)
        manifest['features'] = dict(manifest.get('features', {}), peer_culling_split=True,
                                    surface_refinement=surface, herb_planters=herbs,
                                    snow_deposition=snow, stage_roof_craft=stage, cloud_depth=cloud)
        return rows, manifest

    for surface, herbs, snow, stage, cloud in itertools.product((False, True), repeat=5):
        rows, manifest = fixture(surface, herbs, snow, stage, cloud)
        ok, detail = check(rows, manifest)
        tests.expect('cloud_synthetic_feature_matrix', 'SYNTHETIC surface/herb/snow/stage/cloud '+repr((surface, herbs, snow, stage, cloud)), lambda:
                     ok and detail['expectedTotalBatches'] == detail['actualTotalBatches'] == 1051+8*surface-8*herbs+4*stage
                     and detail['actualProtectedBatches'] == detail['expectedProtectedBatches'] == 603
                     and detail['unchangedProtectedBatches'] == 595-8*snow-8*cloud
                     and detail['unchangedProtectedGeometryBatches'] == 595-8*cloud
                     and detail['colorRevisedProtectedBatches'] == 8*snow
                     and detail['geometryRevisedProtectedBatches'] == 8*cloud
                     and detail['exactPeerSplitProtectedBatches'] == 8
                     and detail['unchangedProtectedBatches']+detail['colorRevisedProtectedBatches']+
                         detail['geometryRevisedProtectedBatches']+detail['exactPeerSplitProtectedBatches'] == 603
                     and detail['cloudDepth'] is cloud
                     and detail['actualCloudDepthBatches'] == detail['expectedCloudDepthBatches'] == 8*cloud
                     and detail['separatelyPinnedOriginalStageBatches'] == 15*stage
                     and detail['separatelyPinnedStageRoofCraftBatches'] == 4*stage
                     and detail['exactStageRoofCraftPayloadBatches'] == 4*stage)

    rows, manifest = fixture(True, True, True, True, True)
    before_rows, _ = fixture(True, True, True, True, False)
    indices = {c.key(row): i for i, row in enumerate(rows)}
    for feature in ('peer_culling_split', 'cloud_depth'):
        for flag in FALSE_FLAGS:
            changed = copy.deepcopy(manifest); changed['features'][feature] = flag
            reason = ('features.peer_culling_split must be literal true' if feature == 'peer_culling_split'
                      else 'Protected attributes/index topology changed')
            tests.expect('cloud_literal_gates', feature+' rejects candidate under '+repr(flag), lambda changed=changed, reason=reason:
                         rejects(check(rows, changed), {reason}))
            if feature == 'cloud_depth':
                tests.expect('cloud_literal_gates', 'legacy clouds admitted under '+repr(flag), lambda changed=changed:
                             check(before_rows, changed))
        changed = copy.deepcopy(manifest); del changed['features'][feature]
        reason = ('features.peer_culling_split must be literal true' if feature == 'peer_culling_split'
                  else 'Protected attributes/index topology changed')
        tests.expect('cloud_literal_gates', feature+' absent rejects candidate specifically', lambda changed=changed, reason=reason:
                     rejects(check(rows, changed), {reason}))
        if feature == 'cloud_depth':
            tests.expect('cloud_literal_gates', 'absent cloud feature retains exact legacy clouds', lambda:
                         check(before_rows, changed))
    tests.expect('cloud_literal_gates', 'literal true rejects unchanged old clouds', lambda:
                 rejects(check(before_rows, manifest), {'Protected attributes/index topology changed'}))

    for pair in sorted(BEFORE):
        index = indices[pair]; row = rows[index]
        tests.expect('cloud_reject_float32_illustration', str(pair)+' native-float32 transform is not approved after', lambda index=index, pair=pair:
                     ILLUSTRATION[pair]['geometrySha256'] != AFTER[pair]['geometrySha256'] and
                     rejects(check(rows[:index]+[ILLUSTRATION[pair]]+rows[index+1:], manifest),
                             {'Protected attributes/index topology changed'}, pair))
        tests.expect('cloud_exact_identity', str(pair)+' missing with recounted totals', lambda index=index, pair=pair:
                     rejects(check(rows[:index]+rows[index+1:], manifest), {'Missing batches'}, pair))
        tests.expect('cloud_exact_identity', str(pair)+' duplicate with recounted totals', lambda row=row, pair=pair:
                     rejects(check(rows+[row], manifest), {'Duplicate batches'}, pair))
        for field, value in [('group', row['group']+'/Cell_0_0'), ('group', row['group']+'_Far'),
                             ('group', row['group']+'/Extra'), ('material', 'CloudSeaSilverExtra'),
                             ('material', 'Bark')]:
            changed = dict(row, **{field: value})
            tests.expect('cloud_exact_identity', str(pair)+' rejects alias '+str(c.key(changed)), lambda index=index, changed=changed, pair=pair:
                         rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Missing batches','Extra/unapproved batches'}, pair))
            tests.expect('cloud_exact_identity', 'alias does not canonicalize '+str(c.key(changed)), lambda changed=changed:
                         c.canonical_key(*c.key(changed)) == c.key(changed))
        for field in ('geometrySha256', 'attributesAndIndicesSha256'):
            for value in (None, '', '0'*64, 'f'*64, BEFORE[pair][field]):
                changed = dict(row, **{field: value})
                tests.expect('cloud_exact_payload', str(pair)+' wrong '+field+' '+repr(value), lambda index=index, changed=changed, pair=pair:
                             rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Protected attributes/index topology changed'}, pair))
            changed = dict(row); del changed[field]
            tests.expect('cloud_exact_payload', str(pair)+' missing '+field, lambda index=index, changed=changed, pair=pair:
                         rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Protected attributes/index topology changed'}, pair))
        for field in ('vertices', 'triangles'):
            for offset in (-1, 1):
                changed = dict(row, **{field: row[field]+offset})
                tests.expect('cloud_exact_counts', str(pair)+' changed '+field+' '+str(offset), lambda index=index, changed=changed, pair=pair:
                             rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Protected attributes/index topology changed'}, pair))
        for field in FIELDS:
            for mode in ('missing', 'changed'):
                altered = copy.deepcopy(baseline)
                target = next(r for r in altered['protectedGroups'] if c.key(r) == pair)
                if mode == 'missing': del target[field]
                else: target[field] = target[field]+1 if field in ('vertices','triangles') else AFTER[pair][field]
                # Under cloud-on, count changes may also cause payload drift;
                # admission of this exact before pin must nevertheless fail.
                def before_pin_rejected(altered=altered, pair=pair):
                    ok, detail = check(rows, manifest, altered)
                    return not ok and {'reason':'Cloud before summary differs from pinned baseline','key':pair} in detail['errors']
                tests.expect('cloud_baseline_before_pins', str(pair)+' '+mode+' '+field, before_pin_rejected)
        changed = dict(row, geometrySha256=AFTER[pair]['geometrySha256'],
                       attributesAndIndicesSha256=BEFORE[pair]['attributesAndIndicesSha256'])
        tests.expect('cloud_exact_payload', str(pair)+' geometry-only approval cannot bypass full payload', lambda index=index, changed=changed, pair=pair:
                     rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Protected attributes/index topology changed'}, pair))
    for pair in [('Landscape/CloudSea_Extra', 'CloudSeaSilver'), ('Landscape/CloudSea_Near_North', 'CloudSeaSilver'),
                 ('Landscape/CloudSea_Near_NW', 'CloudSeaSilverExtra')]:
        extra = dict(template, group=pair[0], material=pair[1])
        tests.expect('cloud_no_prefix_exemption', str(pair)+' extra with recounted totals', lambda extra=extra, pair=pair:
                     rejects(check(rows+[extra], manifest), {'Extra/unapproved batches'}, pair))
    for pair in sorted(protected-set(BEFORE)):
        index = indices[pair]; changed = dict(rows[index], attributesAndIndicesSha256='0'*64)
        tests.expect('cloud_other_protected', str(pair)+' protected under all five feature gates', lambda index=index, changed=changed, pair=pair:
                     rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Protected attributes/index topology changed'}, pair))
    for pair in sorted(STAGE_ORIGINAL):
        index=indices[pair]; changed=dict(rows[index], attributesAndIndicesSha256='0'*64)
        tests.expect('cloud_separate_stage_pin', str(pair)+' original stage remains separately protected', lambda index=index, changed=changed, pair=pair:
                     rejects(check(rows[:index]+[changed]+rows[index+1:], manifest), {'Original stage attributes/index topology changed'}, pair))
    # Final v2.12 stage additions are now independently pinned as well. They
    # remain additional to the core 603, alongside the separate original 15.
    tests.expect('cloud_stage_approved_pins', 'four independent final-stage pins remain exact under cloud gate', lambda:
                 len(c.STAGE_ROOF_CRAFT_PAYLOADS) == 4 and
                 {(g,m): dict(vertices=nv,triangles=nt,geometrySha256=geo,attributesAndIndicesSha256=attr)
                  for g,m,nv,nt,geo,attr in c.STAGE_ROOF_CRAFT_PAYLOADS} == STAGE_APPROVED
                 and set(STAGE_APPROVED) == STAGE_ADDED
                 and not STAGE_ADDED & protected
                 and sum(row['vertices'] for row in STAGE_APPROVED.values()) == 39892
                 and sum(row['triangles'] for row in STAGE_APPROVED.values()) == 25012)
    for pair in sorted(STAGE_ADDED):
        index=indices[pair]
        for field in FIELDS:
            changed=dict(rows[index])
            changed[field]=changed[field]+1 if field in ('vertices','triangles') else '0'*64
            tests.expect('cloud_stage_approved_pins', str(pair)+' rejects changed final-stage '+field, lambda index=index, changed=changed, pair=pair:
                         rejects(check(rows[:index]+[changed]+rows[index+1:],manifest),
                                 {'Approved stage-roof detail payload changed'},pair))

    def array_cases(payloads, after, category):
        fixture_rows, fixture_manifest = fixture(True, True, True, True, after)
        lookup = {c.key(row): i for i, row in enumerate(fixture_rows)}
        selected = [batch for batch in payloads if c.key(batch) in BEFORE]
        tests.expect(category, 'all eight exact cloud identities once', lambda:
                     len(selected)==8 and {c.key(batch) for batch in selected} == set(BEFORE))
        for original in selected:
            pair = c.key(original); index = lookup[pair]
            combined = fixture_rows[:index]+[c.summarize(original)]+fixture_rows[index+1:]
            tests.expect(category, str(pair)+' unmodified native payload admitted before mutations', lambda combined=combined:
                         check(combined, fixture_manifest))
            if not after:
                illustrated = dict(original, vertices=original['vertices'].copy())
                illustrated['vertices'][:,2] = 124.0 - (124.0 - illustrated['vertices'][:,2]) * 2.2
                illustrated_summary = c.summarize(illustrated)
                enabled_rows, enabled_manifest = fixture(True, True, True, True, True)
                combined = enabled_rows[:index]+[illustrated_summary]+enabled_rows[index+1:]
                tests.expect('cloud_reject_float32_illustration', str(pair)+' real native-float32 operation matches forbidden oracle and fails true gate', lambda combined=combined, pair=pair, illustrated_summary=illustrated_summary:
                             illustrated_summary == ILLUSTRATION[pair] and
                             rejects(check(combined,enabled_manifest), {'Protected attributes/index topology changed'}, pair))
            for mutation in ('x_ulp','y_ulp','z_ulp','u_ulp','v_ulp','red_bit','green_bit','blue_bit','alpha_bit',
                             'winding','index','duplicate_triangle','remove_triangle','extra_vertex','remove_vertex','split_shared_vertex'):
                changed = dict(original, **{field: original[field].copy() for field in ('vertices','uv','colors','faces')})
                vertex=int(changed['faces'][0,0])
                if mutation in ('x_ulp','y_ulp','z_ulp','u_ulp','v_ulp'):
                    field='vertices' if mutation[0] in 'xyz' else 'uv'
                    axis=('xyz' if field=='vertices' else 'uv').index(mutation[0])
                    changed[field][vertex,axis]=np.nextafter(changed[field][vertex,axis],np.float32(np.inf))
                elif mutation.endswith('_bit'):
                    axis={'red_bit':0,'green_bit':1,'blue_bit':2,'alpha_bit':3}[mutation]
                    changed['colors'][vertex,axis]^=1
                elif mutation=='winding': changed['faces'][0]=changed['faces'][0,[0,2,1]]
                elif mutation=='index': changed['faces'][0,0]=(vertex+1)%len(changed['vertices'])
                elif mutation=='duplicate_triangle': changed['faces']=np.concatenate([changed['faces'],changed['faces'][:1]])
                elif mutation=='remove_triangle': changed['faces']=changed['faces'][1:]
                elif mutation=='remove_vertex':
                    for field in ('vertices','uv','colors'): changed[field]=changed[field][:-1]
                else:
                    for field in ('vertices','uv','colors'):
                        changed[field]=np.concatenate([changed[field],changed[field][vertex:vertex+1]])
                    if mutation=='split_shared_vertex': changed['faces'][0,0]=len(changed['vertices'])-1
                combined=fixture_rows[:index]+[c.summarize(changed)]+fixture_rows[index+1:]
                tests.expect(category, str(pair)+' rejects real '+mutation, lambda combined=combined, pair=pair:
                             rejects(check(combined,fixture_manifest), {'Protected attributes/index topology changed'}, pair))
    if batches is not None:
        array_cases(batches, current_manifest.get('features',{}).get('cloud_depth') is True,
                    'cloud_current_native_arrays')
    if cloud_candidate_batches is not None:
        tests.expect('cloud_isolated_after_arrays', 'isolated fixture contains only eight clouds', lambda:
                     len(cloud_candidate_batches)==8 and {c.key(b) for b in cloud_candidate_batches}==set(AFTER))
        tests.expect('cloud_isolated_after_arrays', 'isolated fixture exactly matches independent after oracle', lambda:
                     {c.key(b):c.summarize(b) for b in cloud_candidate_batches}==AFTER)
        array_cases(cloud_candidate_batches, True, 'cloud_isolated_after_arrays')
        if batches is not None and current_manifest.get('features',{}).get('cloud_depth') is not True:
            old_arrays={c.key(b):b for b in batches if c.key(b) in BEFORE}
            for after in cloud_candidate_batches:
                pair=c.key(after); before=old_arrays[pair]
                tests.expect('cloud_isolated_preservation', str(pair)+' exact XY/UV/Color32/indices with changed Z', lambda before=before, after=after:
                             before['vertices'][:,:2].tobytes()==after['vertices'][:,:2].tobytes()
                             and not np.array_equal(before['vertices'][:,2],after['vertices'][:,2])
                             and all(before[field].tobytes()==after[field].tobytes() for field in ('uv','colors','faces')))

    if root is not None:
        raw_reader=Path.read_bytes
        for name, expected_error in ((c.BASELINE_NAME,'Frozen v2.8 peer baseline file hash changed'),
                                     (c.STAGE_BASELINE_NAME,'Frozen v2.10 original-stage baseline file hash changed')):
            def corrupt(path,name=name):
                raw=raw_reader(path)
                return raw+b' ' if path.name==name else raw
            with patch.object(Path,'read_bytes',corrupt):
                def reject_pin(expected_error=expected_error):
                    ok,detail=c.validate_peer_culling(root,counted(rows,manifest))
                    return not ok and detail=={'reason':'Invalid peer-culling input','error':expected_error}
                tests.expect('cloud_baseline_file_admission', name+' whitespace fails exact admission error',reject_pin)
            def missing(path,name=name):
                if path.name==name: raise FileNotFoundError(name)
                return raw_reader(path)
            with patch.object(Path,'read_bytes',missing):
                def reject_missing(name=name):
                    ok,detail=c.validate_peer_culling(root,counted(rows,manifest))
                    return not ok and detail=={'reason':'Invalid peer-culling input','error':name}
                tests.expect('cloud_baseline_file_admission', name+' missing fails exact admission error',reject_missing)
    for field in ('visualMeshCount','visualTriangles'):
        changed=counted(rows,manifest); changed[field]+=1
        tests.expect('cloud_manifest_counts', field+' independently enforced', lambda changed=changed:
                     rejects(c.validate_summaries(rows,changed,baseline),{'Manifest export count mismatch'}))
    # Re-run the existing helpers with a synthetic cloud-on input to prove their
    # old paths are valid before an integrated cloud export exists.
    from test_herb_planter_roster_contract import run_roster_cases
    from test_scenery_revision_contract import run_scenery_cases
    run_roster_cases(rows,manifest,baseline,tests)
    run_scenery_cases(rows,manifest,baseline,tests,root=root)
    tests.expect('cloud_independent_pins','validation never mutates baseline object',lambda:baseline==baseline_before)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--cloud-candidate',type=Path,help='Optional isolated true-source after fixture, never a future integrated export')
    args=parser.parse_args()
    from test_peer_culling_contract import Tests
    tests=Tests()
    try:
        baseline=c.load_baseline(args.root)
        data=args.root/'Assets/TreeTopYokocho/Data'
        manifest=json.loads((data/'WorldManifest.json').read_text())
        batches=c.read_visual(data/'VisualMeshes.bytes')
        rows=[c.summarize(batch) for batch in batches]
        tests.expect('actual_export','current export only, with its actual feature flags',lambda:c.validate_peer_culling(args.root,manifest))
        candidate=c.read_visual(args.cloud_candidate) if args.cloud_candidate else None
        if args.cloud_candidate:
            tests.expect('cloud_isolated_after_arrays','isolated authoritative native file SHA',lambda:
                         hashlib.sha256(args.cloud_candidate.read_bytes()).hexdigest()==CLOUD_CANDIDATE_PIN)
        run_cloud_cases(rows,manifest,baseline,tests,batches=batches,root=args.root,cloud_candidate_batches=candidate)
    except Exception as error:
        tests.failures.append(dict(test='suite setup',error=str(error),exception=type(error).__name__))
    print(json.dumps(dict(status='FAIL' if tests.failures else 'PASS',count=tests.count,categories=tests.categories,
                         failures=tests.failures,scope='Current native input; SYNTHETIC mixed-feature summaries; optional ISOLATED cloud after arrays. No future integrated cloud export, generation, render or runtime claim.'),indent=2))
    return bool(tests.failures)


if __name__=='__main__':
    raise SystemExit(main())
