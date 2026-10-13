"""Exact, opt-in source batch-partition and explicit revision roster contract.

No fuzzy group normalization, coordinate tolerance, geometry generation, or
baseline refresh occurs here. This does not measure Unity FPS or draw calls.
"""
from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

import numpy as np

BASELINE_FILE_SHA256 = '32d6506ca35e199501902dd8b1655330ca4742ad4e219619bc46c8a482d87d81'
BASELINE_NAME = 'verified_peer_culling_2.8.0.json'
STAGE_BASELINE_NAME = 'verified_stage_original_payloads_2.10.0.json'
STAGE_BASELINE_FILE_SHA256 = '6f93f57172d2b6dbe71e49c2b75de0a910805f109fdfe09e93456f7570e81e2c'
OLD_KEYS = tuple(
    [('Landscape/DetailLeaves_Peer_Near', 'FoliageScenerySpray' + str(i)) for i in range(3)]
    + [('Landscape/DetailTwigs_Peer_Near', 'Bark')]
)
NEW_TO_OLD = {
    (group.replace('_Peer_Near', '_Peer_' + side + '_Near'), material): (group, material)
    for group, material in OLD_KEYS for side in ('East', 'West')
}
PEER_PREFIXES = ('Landscape/DetailLeaves_Peer', 'Landscape/DetailTwigs_Peer')
# Explicit, separately gated unprotected additions from the reviewed roof pass.
# Existing Joinery batches/materials remain governed by the frozen base roster.
SURFACE_REFINEMENT_BATCHES = (
    ('Shops/S01/Joinery', 'RoofCopper'),
    ('Shops/S02/Joinery', 'RoofCopper'),
    ('Shops/S03/Joinery', 'RoofCopper'),
    ('Shops/S04/Joinery', 'RoofCopper'),
    ('Shops/S05/Joinery', 'RoofCopper'),
    ('Shops/S06/Joinery', 'RoofCopper'),
    ('Shops/S07/Joinery', 'RoofCopper'),
    ('Shops/S08/Joinery', 'RoofCopper'),
)
# Explicit plant-only removals and replacements within existing shop groups.
# Nothing is normalized by shop prefix, Cell/Far suffix, or material family.
# These are unprotected identities; they cannot relax protected payload checks.
HERB_PLANTER_SHOPS = (
    ('Shops/S01', 'HerbClayOchre'), ('Shops/S02', 'HerbClayOchre'),
    ('Shops/S03', 'HerbClayUmber'), ('Shops/S04', 'HerbClayUmber'),
    ('Shops/S05', 'HerbClayOchre'), ('Shops/S06', 'HerbClayOchre'),
    ('Shops/S07', 'HerbClayUmber'), ('Shops/S08', 'HerbClayUmber'),
)
HERB_PLANTER_REMOVED_BATCHES = tuple(
    (group, material) for group, _ in HERB_PLANTER_SHOPS
    for material in ('Food', 'Foliage0', 'Foliage1', 'Foliage2', 'Foliage3')
)
HERB_PLANTER_ADDED_BATCHES = tuple(
    (group, material) for group, clay in HERB_PLANTER_SHOPS
    for material in ('HerbSoil', 'HerbLeafDeep', 'HerbLeafYoung', clay)
)
# Eight explicit Color32 RGB revisions. Before hashes belong to the immutable
# v2.8 file; after hashes were reviewed against the actual v2.10 native overlay.
# The gate changes ONLY attributesAndIndicesSha256. Frozen geometry/counts and
# all UV/alpha/index bytes remain covered by those exact after payload hashes.
SNOW_DEPOSITION_REVISIONS = (
    ('Landscape/SnowRange_0', 'AlpineSnow',
     '41fc6db1aba35e1d7dfa94d0aff85d73b9074e23c05ee8650fd485dcee3e8618',
     '78d932fa17182d8796aa176ca091924ab7425c8b707311a4983998abdc1d06db'),
    ('Landscape/SnowRange_0', 'AlpineSnowShade',
     'de0784b4acd480c95f560e5887510cd431627796cd92b54e10267ced84c47656',
     '54dc6ef6dde6cfe62add9021d3667f333daeffa4b3a7e01707244ec92f64fde7'),
    ('Landscape/SnowRange_1', 'AlpineSnow',
     '0f8b11c81bb07ea863ae1c5757c861000d5b657d2dcfef3a22da644202d699f9',
     '955a599ebc5f64999266b94d0d239b36c889a1ea610e14ff12aded27fe41c821'),
    ('Landscape/SnowRange_1', 'AlpineSnowShade',
     '2e30bc645036ed2264c4b56ca929d0d71251de7a0d7250695396f8da38315a17',
     'a31d8b056968ea5a132c6d0f27004f8dd92ceefb42af167cd5439698cd7c2825'),
    ('Landscape/SnowRange_2', 'AlpineSnow',
     '63645107cf505f488cf26cd0633e41f9b7a6a0c9281d386f1233c196327af4ec',
     '83f41635fc969571b67f33e6e07f3cff4177aeefaa6669bf56b888bac821fa6a'),
    ('Landscape/SnowRange_2', 'AlpineSnowShade',
     '9261f575f655f37699ba9f2fb33e605f7cd837ffdaaecb3d7835414c5ace8026',
     'cd409e7e28b21de58166ecb2f900c83d5a98790567b1a5554d5b33cabe929662'),
    ('Landscape/SnowRange_3', 'AlpineSnow',
     '3c2947b696f27c94dd5e0c2e353b0c93d1cae3410a156638a76cdf48731ec565',
     '7d61d1bd83d2ba474d884e84f4f07eddbfb05fd7427b6bea1ad042a268ba4460'),
    ('Landscape/SnowRange_3', 'AlpineSnowShade',
     '81156765e75251ad1432f07d495a59b68d312f792e3eb52e62fb630839d890be',
     '255678dcf69988b03a7bb0fc210005a330c4611b28c105f2948c98a43e5f4f69'),
)
# Eight explicit source-float64 Z revisions, compacted once to native float32.
# Before identities, counts and both hashes are already pinned in the immutable
# v2.8 baseline. Only the approved after geometry/full-payload hashes substitute;
# XY/UV/Color32/index bytes and all counts remain exact. No prefix or tolerance.
CLOUD_DEPTH_REVISIONS = (
    ('Landscape/CloudSea_Near_NW', 'CloudSeaSilver', 2916, 5184,
     '3ed9b7861849c3a2b98aace773ef719429c75ca54caba692da6d24c331fd7804',
     '39533559fe10ceea7b430cf9a7bfe8c5b70f13cf658ff584906c01ecdeeaef30',
     '97006ec2205d260f92d1426386f3732e17799d63fb28883fb518ba25fea5cd30',
     '192c639efd14684157a634527fc2029d190dc76b479b87da17e9c94cfdd0cb2c'),
    ('Landscape/CloudSea_Near_NE', 'CloudSeaSilver', 2916, 5184,
     '46d94503497325c5ea4cc5cf79d3ba92a08e46e031710960c3ead478b94c6b8e',
     '174931185601eb5e324e628d01af77c0dfb7ff50f59732bf096661a3142e12be',
     '1187b789653e92bcc423626d95b34f02ce32c36197ee8ffe4755e944012c7bba',
     '0d2bed6a4cbcfd6dbf0c512724650234506d54bc6971cd3e3921599e4cac2f6d'),
    ('Landscape/CloudSea_Near_SW', 'CloudSeaSilver', 1458, 2592,
     'daa45ed940a0e36ef256681b0a8572c86d814e2b06398a3deb620719cbdaf579',
     '8a24940b02540daafcaa6ed6775463cddad807fd258706cd6be8aff81083b123',
     'c410e6dcab05841783685dca8d545a84cbff90aade9cb43d27ad287b8df23a09',
     '3f65d7b9cddc906f2f762cdb9775599d44944ea7c1bf339cf6a3fbbdda7366b5'),
    ('Landscape/CloudSea_Near_SE', 'CloudSeaSilver', 1458, 2592,
     'c2490b2025c0aa5eecf298420ed3860b24e54f107a8e7f4965e3cbcbefd7d048',
     '9bf0bbc206865d717693d1da5f92ad23144dfd76bd95ab79d155c5c74e2aa59e',
     '9997de3a3814b86b2b24aac6ae1c46b6a9df3d84cf3e727c388b2cc28cd11379',
     '30df1cf7353beb68886f0acb563a3ae819146bad2f231c466e3c3ac4edc7c2bc'),
    ('Landscape/CloudSea_Far_NW', 'CloudSeaSilver', 3645, 6480,
     '064b002f169e9c74a443b2814061a4e4318f8e40759e114a5918ad050abcc903',
     '1e002e29019330aa4a436d0785c9e017dc22cc794ef4c4f97fcb6d77c1330530',
     '40da297159ab0045dc60c5cf0229a23ff325132679fbfec5fcdbb7f6eb1d8a9f',
     '1ca464e0853e9f1c7e259822380ba00e63ce808841293428cee47521ea4ab62b'),
    ('Landscape/CloudSea_Far_NE', 'CloudSeaSilver', 3645, 6480,
     '0c21786caa3cd19e975db07ee4d822e5287e4d0381abc164640b56fac2af2058',
     'ebea8081e313aa451c23f98682eaa36f1ef909fc258c3983fa1748e479055745',
     '99eeb4951945d559111b05b7334629fffc7d755bca27c9ec4043b5e07bb58267',
     '9a2595032e5a1d6f0d58d29d2a1510ebeb48b7d51c04cd206b3d2f387337411c'),
    ('Landscape/CloudSea_Far_SW', 'CloudSeaSilver', 2187, 3888,
     'fb07f9b4407f8e342c8c0e3c906115e4fe5105c010edebfde64754e723c5a102',
     '9bfdd02a508d94559410c5c4a18c54490735566d4c2d1ab56fdf5b9f7c9f551e',
     '9c2656172ea19f809e6877c19817269f2a98ca8d73fbebce636eae1faed55743',
     '01271b20d6ed0d3c520441e248e07d1c17b40346f32febec4cb5cc31f67a9798'),
    ('Landscape/CloudSea_Far_SE', 'CloudSeaSilver', 2187, 3888,
     '30fdb909b53a6c556c0c0e57cbd196ab1df41712c3d731b1e88c9a41947b1b19',
     '1066eddde531ee7d1ce0e0d0bbf95d53ca68adb9456aa4f096262e7121d0affe',
     '4a5d45d82158d00cffd21a97ed276d1f1c7ecba6886aa1ea9af51fa509a79961',
     '99d15f1aa5540b08a8f692a9fc0836f0c13e1479382f1e929abbd82d51818ba2'),
)
# Exact identity allowlist plus the final independently verified native payloads.
# Four reviewed curved-roof additions; never a Stage prefix exemption.
STAGE_ROOF_CRAFT_BATCHES = (
    ('Stage/Noh/RoofDetail/Courses', 'Kawara'),
    ('Stage/Noh/RoofDetail/Caps', 'Kawara'),
    ('Stage/Noh/RoofDetail/Joinery', 'StageCypress'),
    ('Stage/Noh/RoofDetail/Joinery', 'DarkTimber'),
)
# Frozen after the nine-station curved proposal was finalized and independently
# verified in the complete v2.12 native export, SHA750c0607...d1822. This is an
# additional approval pin, not a refresh of either existing original baseline.
STAGE_ROOF_CRAFT_PAYLOADS = (
    ('Stage/Noh/RoofDetail/Courses', 'Kawara', 34944, 21904,
     'b0b44cf78739cf6e806bcc2dd753e68bc0f72e8002b9828f5d9c4bd73dce6bf4',
     '9c44deeb8195c430346986194cc9f32cde16b6cf67a11b236d4f4a810666b400'),
    ('Stage/Noh/RoofDetail/Caps', 'Kawara', 3444, 2132,
     'f0dae0231b33d8c6e6a5a81c83d1f8f65cd6c0c09e5375f5d2ffd22c5670054c',
     'c5a357b8b85fa58fc1c789c109ef48b5cd0797bcf6a249e9a8234953671ef54f'),
    ('Stage/Noh/RoofDetail/Joinery', 'DarkTimber', 448, 480,
     'd58f33c32bc2d65dde4a1d548c734b30fabedbf8fa283d4394d241ba13fa4937',
     '13eeefa5b287f041e7f414291f0502e3619c0953e2908c95a069eddfce046fcc'),
    ('Stage/Noh/RoofDetail/Joinery', 'StageCypress', 1056, 496,
     'b1747df562bb944ce60e5139d26c1b2cfeb7d7e2b83a52fb11d863e357437e84',
     'ac1dd6ea8f5e5fc456730280036068848b886ba27350012404ee7889eea8fdff'),
)
# The original 15 stage records are only IDENTITIES in the old unprotected roster.
# Preserve their verified v2.10 native payloads separately under the craft gate.
# Do not miscount these as part of the original 603 protected geometry records.
STAGE_ORIGINAL_SOURCE_COMMIT = 'bdb8c62b8133a1821ec521efd86851cb2f750ceb'
STAGE_ORIGINAL_NATIVE_SHA256 = 'c41888a0dcb663f9fa08ef411c3c6ed09317d5b173b921e5f10721b83b9d5d71'
STAGE_ORIGINAL_PAYLOADS = (
    ('Stage/Noh/Floor', 'Bronze', 448, 672,
     '1b30171daf7032726c7b77e5d40ba2cccaab768e725d21d2ec10df05c8599460',
     'c77afff55f61a4c0ff7d487eb5523cca607e8db92f457f86576ddbdc971fadae'),
    ('Stage/Noh/Floor', 'DarkTimber', 24, 12,
     '49c970a624222e7cd742064bee18d04a347b42fed293c6ba7418d2c27d0487f7',
     '2687591f08a2289b88280a89990b77ac3c8f7211582f36b380005a646f224176'),
    ('Stage/Noh/Floor', 'StageCypress', 432, 216,
     '1394c15ae4846b0a5eacda7a3d8093a864cfb2c2f2081a0388f752d1edf0da01',
     'bc2a736ab57e4813f6b9ba1a875d003be8121c5b6d11a3d79399bb5fd96a6002'),
    ('Stage/Noh/HipRoof', 'DarkTimber', 22, 14,
     '2439750110d07010f2f362e117778f71353c2ce73e98753a80e930f7cc5b7853',
     '44986c1339e4773785695646c0ea1e160ee9f892e75e21926b83a6d4130375e6'),
    ('Stage/Noh/HipRoof', 'Kawara', 394, 310,
     '9eba91224fc06d62628c973ff9670c8367c30f8b56aa3abf0141707b964cd45d',
     '912cf36e684402f37d2ec104c3f24d38ed266e5f9d372b3003c408fe05897bad'),
    ('Stage/Noh/HipRoof', 'StageCypress', 672, 336,
     '0a5e5eb9026cf131db1dbbe7b231b30a394c0f89dc83c54f48eefb4113ebe80a',
     'c7fa63c46bf512534f90f081565f406efd20505fe20601909a223ee0c243536f'),
    ('Stage/Noh/Lighting', 'Bronze', 3204, 4756,
     'a3bfe020203f74bd3abdd0585a581dc0b9ad95ef3c1adb92ea218f7f30ec2a2d',
     '4494c6d97549fa63e459d7fa9e554033864176b1f13b67a9169766e63ae38143'),
    ('Stage/Noh/Lighting', 'Iron', 424, 604,
     '5e8754db4c9f882450228bb6fc8a8546a4afaaeb69d2ea05253f12543bb5a8fa',
     '73deb6a7bd3ee83d05b5f3a7e85bb998cca00214f93c9efc01f088e78ad5a29e'),
    ('Stage/Noh/Lighting', 'PaperLight', 650, 1152,
     '68a2cb7c9bd9e73563eb1676a609bc52c065c84a831d24c7b80cec1f52db326c',
     '5f964e5e048572b8ef26ff7e31085ea2a44f37c7650a9cf6864284447b4cffd9'),
    ('Stage/Noh/PineCrest', 'Bronze', 312, 156,
     '5e9ea91b69d323b865b1fac194f0caf279c7b695f97bf51871b7d2c28cc4d9b4',
     '8c6db425f500410b329fbe28e3433296aaa763d8ec13d886feac6e83624ad562'),
    ('Stage/Noh/PineCrest', 'DarkTimber', 24, 12,
     'bcbd725e863e3dfbdabd8e58ddd91698de7f30b4473a0713bbf6c5a1fb994a9e',
     '74ccf65480c54adff209d5dc1179d4179f61e45db7c5f6ae235c06458c829c84'),
    ('Stage/Noh/Posts', 'Bronze', 96, 48,
     '594c9b3a522f7e4d969fdc05e2a800164538cd6390e863304031b2b0c71b06bd',
     'ab1c489a76979db0533a8a632cbf3794e3a53bbbe8a8aa17fa3006bfdaefafb1'),
    ('Stage/Noh/Posts', 'StageCypress', 768, 384,
     '5ec22298ecbc89ef37eb8f258a67209efaefa1c97aace2c97d03fade83c3a71c',
     'ac8891968c429eca0105064e719c9be7de0c089ae9feceb6bedb8e2f40b89b0c'),
    ('Stage/Noh/Support', 'Cedar', 72, 36,
     'b71911decd9135327ca76468c596e6753facba5117bcdd949b8366b72915aa3d',
     '46deae1ec6c845f7c34cfad35fdac9b400a8864545dee1cb26b254dfb2c27207'),
    ('Stage/Noh/Support', 'DarkTimber', 120, 60,
     '7335bcbf54ffd0660a0ff1813127648613a620166454474f54174c73d148ea5c',
     'b55995510dc9acc6f47fcd5cdb44db59ad827111f60c9dd829ec785250a8e813'),
)

BRANCH_KEY = ('Tree/SupportingBranches', 'Bark')
BRANCH_AFTER_SHA256 = '8f6573d1bb4f319d7998c5371aa0fb9b7c894b3e56982476ffdfceb87492c48d'


def key(batch):
    return batch['group'], batch['material']


def enabled(manifest):
    features = manifest.get('features', {})
    return isinstance(features, dict) and features.get('peer_culling_split') is True


def read_visual(path):
    """Retain all authored attributes and duplicate batches; reject bad payloads."""
    payload_size = Path(path).stat().st_size

    def exact(stream, length):
        if length < 0 or length > payload_size - stream.tell():
            raise ValueError('Declared JYWM field exceeds remaining payload')
        raw = stream.read(length)
        if len(raw) != length:
            raise ValueError('Truncated JYWM payload')
        return raw

    result = []
    with Path(path).open('rb') as stream:
        if exact(stream, 4) != b'JYWM':
            raise ValueError('Invalid JYWM signature')
        version, count = struct.unpack('<II', exact(stream, 8))
        if version != 1:
            raise ValueError('Unsupported JYWM version')
        for _ in range(count):
            group, material = [exact(stream, struct.unpack('<I', exact(stream, 4))[0]).decode('utf-8')
                               for _ in range(2)]
            nv, ni = struct.unpack('<II', exact(stream, 8))
            if ni % 3:
                raise ValueError('Non-triangular index count')
            vertices = np.frombuffer(exact(stream, nv * 12), '<f4').reshape(-1, 3)
            uv = np.frombuffer(exact(stream, nv * 8), '<f4').reshape(-1, 2)
            colors = np.frombuffer(exact(stream, nv * 4), 'u1').reshape(-1, 4)
            faces = np.frombuffer(exact(stream, ni * 4), '<u4').reshape(-1, 3)
            if (not np.isfinite(vertices).all() or not np.isfinite(uv).all()
                    or (ni and int(faces.max()) >= nv)):
                raise ValueError('Nonfinite attributes or out-of-range indices')
            result.append(dict(group=group, material=material, vertices=vertices,
                               uv=uv, colors=colors, faces=faces))
        if stream.read(1):
            raise ValueError('Unexpected trailing JYWM bytes')
    return result


def attribute_vertices(batch):
    return np.concatenate((np.asarray(batch['vertices'], dtype='<f4').view('u1').reshape(-1, 12),
                           np.asarray(batch['uv'], dtype='<f4').view('u1').reshape(-1, 8),
                           np.asarray(batch['colors'], dtype='u1').reshape(-1, 4)), axis=1)


def triangle_records(batch):
    """Cyclic rotation only: preserve winding, all 24-byte attributes, multiplicity."""
    triangles = attribute_vertices(batch)[batch['faces']]
    rotations = np.stack([triangles, np.roll(triangles, -1, axis=1),
                          np.roll(triangles, -2, axis=1)], axis=1)
    records = rotations.reshape(-1, 3, 72).copy().view('V72').reshape(-1, 3)
    records.sort(axis=1)
    return records[:, 0].copy()


def triangle_fingerprint(batches):
    arrays = [triangle_records(batch) for batch in batches]
    records = np.concatenate(arrays) if arrays else np.empty(0, dtype='V72')
    records.sort()
    return dict(triangles=len(records), sha256=hashlib.sha256(records.tobytes()).hexdigest())


def canonical_key(group, material):
    """Exactly eight allowed (group, material) pairs; no regex or Cell aliases."""
    return NEW_TO_OLD.get((group, material), (group, material))


def raw_attributes(batch):
    return b''.join((np.asarray(batch['vertices'], dtype='<f4').tobytes(),
                     np.asarray(batch['uv'], dtype='<f4').tobytes(),
                     np.asarray(batch['colors'], dtype='u1').tobytes(),
                     np.asarray(batch['faces'], dtype='<u4').tobytes()))


def summarize(batch):
    vertices = np.asarray(batch['vertices'], dtype='<f4')
    faces = np.asarray(batch['faces'], dtype='<u4')
    return dict(group=batch['group'], material=batch['material'], vertices=len(vertices),
                triangles=len(faces),
                geometrySha256=hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest(),
                attributesAndIndicesSha256=hashlib.sha256(raw_attributes(batch)).hexdigest())


def partition_peer(batch):
    """Frozen-input fixture only: induced X-half-space partition with exact indices.

    Every original vertex occurs once. No triangle may cross the dividing plane.
    Preserve vertex order and face order within each side, including unused vertices.
    This function is NOT called by the acceptance validator.
    """
    if key(batch) not in OLD_KEYS:
        raise ValueError('Only four pinned old peer batches can be partitioned')
    x = batch['vertices'][:, 0]
    if np.any(x == 0):
        raise ValueError('Vertex touches partition plane')
    vertex_side = x > 0
    face_sides = vertex_side[batch['faces']]
    if not np.all(face_sides == face_sides[:, :1]):
        raise ValueError('Partition would break a shared indexed component')
    result = []
    for side, positive in [('East', True), ('West', False)]:
        selected = vertex_side == positive
        face_mask = face_sides[:, 0] == positive
        if not selected.any() or not face_mask.any():
            raise ValueError('Both East and West must be nonempty')
        remap = np.full(len(x), -1, dtype=np.int64)
        remap[selected] = np.arange(int(selected.sum()))
        result.append(dict(group=batch['group'].replace('_Peer_Near', '_Peer_' + side + '_Near'),
                           material=batch['material'], vertices=batch['vertices'][selected],
                           uv=batch['uv'][selected], colors=batch['colors'][selected],
                           faces=remap[batch['faces'][face_mask]].astype('<u4')))
    return result


def load_baseline(root):
    path = Path(root) / 'Docs/baselines' / BASELINE_NAME
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_FILE_SHA256:
        raise ValueError('Frozen v2.8 peer baseline file hash changed')
    return json.loads(raw)


def load_stage_baseline(root):
    """Additional preservation pin; the original 603-record contract is unchanged."""
    path = Path(root) / 'Docs/baselines' / STAGE_BASELINE_NAME
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != STAGE_BASELINE_FILE_SHA256:
        raise ValueError('Frozen v2.10 original-stage baseline file hash changed')
    baseline = json.loads(raw)
    rows = baseline['originalStageGroups']
    actual = tuple((row['group'], row['material'], row['vertices'], row['triangles'],
                    row['geometrySha256'], row['attributesAndIndicesSha256']) for row in rows)
    if actual != STAGE_ORIGINAL_PAYLOADS:
        raise ValueError('Original-stage code pins differ from frozen archive baseline')
    return baseline


def validate_summaries(summaries, manifest, baseline):
    """Exact pinned summaries; only approved snow RGB/cloud Z hashes substitute.

    Call validate_peer_culling for file admission: it verifies both applicable
    frozen baseline byte hashes before parsing/summarizing the actual export.
    """
    errors = []
    if not enabled(manifest):
        errors.append({'reason': 'features.peer_culling_split must be literal true'})
    old = {key(record): record for record in baseline['protectedGroups']}
    split = {key(record): record for record in baseline['splitGroups']}
    expected = {k: record for k, record in old.items() if k not in OLD_KEYS}
    expected.update(split)
    if (len(old) != 599 or len(expected) != 603 or len(split) != 8
            or set(split) != set(NEW_TO_OLD)
            or old.get(BRANCH_KEY, {}).get('geometrySha256') != BRANCH_AFTER_SHA256):
        errors.append({'reason': 'Invalid frozen protection schema or SupportingBranches hash'})
    # Pin the complete legacy roster too. Its 448 otherwise unprotected batches
    # keep exact identities. Only the separate 15 original-stage payload pins
    # below add protection within that roster, and only under the craft gate.
    roster = set(expected) | {tuple(pair) for pair in baseline['unprotectedBatchKeys']}
    features = manifest.get('features', {})
    surface_refinement = (isinstance(features, dict)
                          and features.get('surface_refinement') is True)
    surface_keys = set(SURFACE_REFINEMENT_BATCHES)
    if surface_refinement:
        if len(surface_keys) != 8 or surface_keys & roster:
            errors.append({'reason': 'Invalid explicit roof-refinement addition schema'})
        roster.update(surface_keys)
    herb_planters = (isinstance(features, dict)
                     and features.get('herb_planters') is True)
    herb_removed = set(HERB_PLANTER_REMOVED_BATCHES)
    herb_added = set(HERB_PLANTER_ADDED_BATCHES)
    if herb_planters:
        if (len(herb_removed) != 40 or len(herb_added) != 32
                or not herb_removed <= roster or herb_removed & set(expected)
                or herb_added & roster
                or {group for group, _ in herb_added} != {group for group, _ in herb_removed}):
            errors.append({'reason': 'Invalid explicit herb-planter replacement schema'})
        roster.difference_update(herb_removed)
        roster.update(herb_added)
    snow_deposition = (isinstance(features, dict)
                       and features.get('snow_deposition') is True)
    snow_after = {(group, material): after for group, material, _, after in SNOW_DEPOSITION_REVISIONS}
    snow_keys = set(snow_after)
    if (len(SNOW_DEPOSITION_REVISIONS) != 8 or len(snow_keys) != 8
            or not snow_keys <= set(expected)):
        errors.append({'reason': 'Invalid explicit snow-deposition revision schema'})
    for group, material, before_hash, after_hash in SNOW_DEPOSITION_REVISIONS:
        pair = (group, material)
        frozen = old.get(pair, {})
        if (frozen.get('attributesAndIndicesSha256') != before_hash
                or not isinstance(before_hash, str) or len(before_hash) != 64
                or not isinstance(after_hash, str) or len(after_hash) != 64
                or before_hash == after_hash):
            errors.append({'reason': 'Snow before hash differs from pinned baseline', 'key': pair})
        if snow_deposition and pair in expected:
            # Copy, never mutate the pinned baseline or its geometry/count fields.
            expected[pair] = dict(expected[pair], attributesAndIndicesSha256=after_hash)
    cloud_depth = (isinstance(features, dict)
                   and features.get('cloud_depth') is True)
    cloud_after = {
        (group, material): (after_geometry, after_attributes)
        for group, material, _, _, _, _, after_geometry, after_attributes in CLOUD_DEPTH_REVISIONS
    }
    cloud_keys = set(cloud_after)
    if (len(CLOUD_DEPTH_REVISIONS) != 8 or len(cloud_keys) != 8
            or not cloud_keys <= set(expected) or cloud_keys & snow_keys):
        errors.append({'reason': 'Invalid explicit cloud-depth revision schema'})
    for (group, material, vertices, triangles, before_geometry, before_attributes,
         after_geometry, after_attributes) in CLOUD_DEPTH_REVISIONS:
        pair = (group, material)
        frozen = old.get(pair, {})
        if (tuple(frozen.get(field) for field in
                  ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256'))
                != (vertices, triangles, before_geometry, before_attributes)
                or any(not isinstance(value, str) or len(value) != 64
                       or any(letter not in '0123456789abcdef' for letter in value)
                       for value in (before_geometry, before_attributes, after_geometry, after_attributes))
                or before_geometry == after_geometry or before_attributes == after_attributes):
            errors.append({'reason': 'Cloud before summary differs from pinned baseline', 'key': pair})
        if cloud_depth and pair in expected:
            # Do not rewrite the frozen baseline, counts, identity, or other rows.
            expected[pair] = dict(expected[pair], geometrySha256=after_geometry,
                                  attributesAndIndicesSha256=after_attributes)
    stage_roof_craft = (isinstance(features, dict)
                        and features.get('stage_roof_craft') is True)
    stage_keys = set(STAGE_ROOF_CRAFT_BATCHES)
    stage_approved = {
        (group, material): dict(vertices=vertices, triangles=triangles,
                               geometrySha256=geometry, attributesAndIndicesSha256=attributes)
        for group, material, vertices, triangles, geometry, attributes in STAGE_ROOF_CRAFT_PAYLOADS
    }
    stage_original = {
        (group, material): dict(vertices=vertices, triangles=triangles,
                               geometrySha256=geometry, attributesAndIndicesSha256=attributes)
        for group, material, vertices, triangles, geometry, attributes in STAGE_ORIGINAL_PAYLOADS
    }
    if stage_roof_craft:
        if (len(STAGE_ROOF_CRAFT_BATCHES) != 4 or len(stage_keys) != 4
                or stage_keys & roster
                or len(STAGE_ROOF_CRAFT_PAYLOADS) != 4 or set(stage_approved) != stage_keys
                or sum(row['vertices'] for row in stage_approved.values()) != 39892
                or sum(row['triangles'] for row in stage_approved.values()) != 25012
                or len(STAGE_ORIGINAL_PAYLOADS) != 15 or len(stage_original) != 15
                or not set(stage_original) <= roster or set(stage_original) & set(expected)):
            errors.append({'reason': 'Invalid explicit stage-roof addition/preservation schema'})
        roster.update(stage_keys)
    counts = Counter(key(record) for record in summaries)
    missing = sorted(roster - set(counts))
    extra = sorted(set(counts) - roster)
    duplicate = sorted(k for k, count in counts.items() if count != 1)
    if missing:
        errors.append({'reason': 'Missing batches', 'keys': missing})
    if extra:
        errors.append({'reason': 'Extra/unapproved batches', 'keys': extra})
    if duplicate:
        errors.append({'reason': 'Duplicate batches', 'keys': duplicate})
    drift = []
    for observed in summaries:
        k = key(observed)
        if k in expected:
            wanted = expected[k]
            fields = ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256')
            if any(observed.get(field) != wanted.get(field) for field in fields):
                drift.append(k)
                errors.append({'reason': 'Protected attributes/index topology changed', 'key': k})
        if stage_roof_craft and k in stage_original:
            wanted = stage_original[k]
            fields = ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256')
            if any(observed.get(field) != wanted.get(field) for field in fields):
                errors.append({'reason': 'Original stage attributes/index topology changed', 'key': k})
        if stage_roof_craft and k in stage_approved:
            wanted = stage_approved[k]
            fields = ('vertices', 'triangles', 'geometrySha256', 'attributesAndIndicesSha256')
            if any(observed.get(field) != wanted.get(field) for field in fields):
                errors.append({'reason': 'Approved stage-roof detail payload changed', 'key': k})
    for field, value in [('visualMeshCount', len(summaries)),
                         ('visualTriangles', sum(record['triangles'] for record in summaries))]:
        if type(manifest.get(field)) is not int or manifest[field] != value:
            errors.append({'reason': 'Manifest export count mismatch', 'field': field,
                           'expected': value, 'actual': manifest.get(field)})
    detail = dict(baselineProtectedBatches=599, actualProtectedBatches=sum(counts[k] for k in expected),
                  expectedProtectedBatches=603,
                  unchangedProtectedBatches=595 - 8*int(snow_deposition) - 8*int(cloud_depth),
                  unchangedProtectedGeometryBatches=595 - 8*int(cloud_depth),
                  geometryRevisedProtectedBatches=8 if cloud_depth else 0,
                  colorRevisedProtectedBatches=8 if snow_deposition else 0,
                  exactPeerSplitProtectedBatches=8,
                  replacedOldBatches=4, replacementBatches=8,
                  expectedTotalBatches=len(roster), actualTotalBatches=len(summaries),
                  surfaceRefinement=surface_refinement,
                  expectedSurfaceRefinementBatches=8 if surface_refinement else 0,
                  actualSurfaceRefinementBatches=sum(counts[k] for k in surface_keys),
                  herbPlanters=herb_planters,
                  expectedHerbPlanterBatches=32 if herb_planters else 0,
                  actualHerbPlanterBatches=sum(counts[k] for k in herb_added),
                  expectedLegacyPlantBatches=0 if herb_planters else 40,
                  actualLegacyPlantBatches=sum(counts[k] for k in herb_removed),
                  snowDeposition=snow_deposition,
                  expectedSnowDepositionBatches=8 if snow_deposition else 0,
                  actualSnowDepositionBatches=sum(
                      key(row) in snow_after and row.get('attributesAndIndicesSha256') == snow_after[key(row)]
                      for row in summaries),
                  cloudDepth=cloud_depth,
                  expectedCloudDepthBatches=8 if cloud_depth else 0,
                  actualCloudDepthBatches=sum(
                      key(row) in cloud_after and
                      (row.get('geometrySha256'), row.get('attributesAndIndicesSha256')) == cloud_after[key(row)]
                      for row in summaries),
                  stageRoofCraft=stage_roof_craft,
                  expectedStageRoofCraftBatches=4 if stage_roof_craft else 0,
                  actualStageRoofCraftBatches=sum(counts[k] for k in stage_keys),
                  separatelyPinnedStageRoofCraftBatches=4 if stage_roof_craft else 0,
                  exactStageRoofCraftPayloadBatches=sum(
                      key(row) in stage_approved and all(row.get(field) == value
                          for field, value in stage_approved[key(row)].items()) for row in summaries),
                  separatelyPinnedOriginalStageBatches=15 if stage_roof_craft else 0,
                  actualOriginalStageBatches=sum(counts[k] for k in stage_original),
                  originalStageBaselineFileSha256=STAGE_BASELINE_FILE_SHA256 if stage_roof_craft else None,
                  baselineFileSha256=BASELINE_FILE_SHA256,
                  hashConvention='float32 LE position, float32 LE UV, Color32, uint32 LE indices; exact array order',
                  reviewedSupportingBranchesSha256=BRANCH_AFTER_SHA256,
                  driftedGroups=drift, errors=errors,
                  scope='Exact source batch partition and narrowly gated RGB/Z revisions/additive roster; original and approved added stage payloads separately pinned under craft gate; no measured FPS, draw calls, Unity normals or GPU timing')
    return not errors, detail


def validate_peer_culling(root, manifest, visual_path=None):
    try:
        baseline = load_baseline(root)
        features = manifest.get('features', {})
        if isinstance(features, dict) and features.get('stage_roof_craft') is True:
            load_stage_baseline(root)
        path = visual_path or Path(root) / 'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'
        summaries = [summarize(batch) for batch in read_visual(path)]
        return validate_summaries(summaries, manifest, baseline)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError) as error:
        return False, {'reason': 'Invalid peer-culling input', 'error': str(error)}
