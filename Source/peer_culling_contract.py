"""Exact, opt-in v2.8 -> v2.9 source batch-partition contract.

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


def validate_summaries(summaries, manifest, baseline):
    """Acceptance is exact payload/index equality to the pinned induced partition."""
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
    # Pin the complete batch roster too. The other 448 current, unprotected
    # batches retain their identity, but their geometry is not newly frozen here.
    roster = set(expected) | {tuple(pair) for pair in baseline['unprotectedBatchKeys']}
    features = manifest.get('features', {})
    surface_refinement = (isinstance(features, dict)
                          and features.get('surface_refinement') is True)
    surface_keys = set(SURFACE_REFINEMENT_BATCHES)
    if surface_refinement:
        if len(surface_keys) != 8 or surface_keys & roster:
            errors.append({'reason': 'Invalid explicit roof-refinement addition schema'})
        roster.update(surface_keys)
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
    for field, value in [('visualMeshCount', len(summaries)),
                         ('visualTriangles', sum(record['triangles'] for record in summaries))]:
        if type(manifest.get(field)) is not int or manifest[field] != value:
            errors.append({'reason': 'Manifest export count mismatch', 'field': field,
                           'expected': value, 'actual': manifest.get(field)})
    detail = dict(baselineProtectedBatches=599, actualProtectedBatches=sum(counts[k] for k in expected),
                  expectedProtectedBatches=603, unchangedProtectedBatches=595,
                  replacedOldBatches=4, replacementBatches=8,
                  expectedTotalBatches=len(roster), actualTotalBatches=len(summaries),
                  surfaceRefinement=surface_refinement,
                  expectedSurfaceRefinementBatches=8 if surface_refinement else 0,
                  actualSurfaceRefinementBatches=sum(counts[k] for k in surface_keys),
                  baselineFileSha256=BASELINE_FILE_SHA256,
                  hashConvention='float32 LE position, float32 LE UV, Color32, uint32 LE indices; exact array order',
                  reviewedSupportingBranchesSha256=BRANCH_AFTER_SHA256,
                  driftedGroups=drift, errors=errors,
                  scope='Exact source batch partition only; no measured FPS, draw calls, Unity normals or GPU timing')
    return not errors, detail


def validate_peer_culling(root, manifest, visual_path=None):
    try:
        baseline = load_baseline(root)
        path = visual_path or Path(root) / 'Assets/TreeTopYokocho/Data/VisualMeshes.bytes'
        summaries = [summarize(batch) for batch in read_visual(path)]
        return validate_summaries(summaries, manifest, baseline)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError) as error:
        return False, {'reason': 'Invalid peer-culling input', 'error': str(error)}
