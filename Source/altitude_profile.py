"""Raise the legacy near world without moving ground or distant landscape.

Source coordinates are metres, X east / Y north / Z up. Call exactly once,
after legacy metadata is complete and BEFORE independent high-crown stairs,
clouds and booster props. No Unity coordinate conversion happens here.
"""
from __future__ import annotations

import copy
import math
import numpy as np

GROUND_UNCHANGED_THROUGH = 14.0
TRANSLATION_START = 33.0
ALLEY_LIFT = 100.0
PROFILE_ID = 'GroundFixed_SmoothRise_AlleyPlus100m'
POSITION_KEYS = frozenset(('position', 'center', 'start', 'end', 'destination',
                           'exit', 'target', 'anchor', 'origin', 'min', 'max'))
POINT_LIST_KEYS = frozenset(('points', 'centerline', 'spawns'))
HEIGHT_KEYS = frozenset(('z', 'base', 'top'))
# These are vectors or dimensions, never world positions, even if length three.
UNTOUCHED_KEYS = frozenset(('axes', 'front', 'right', 'forward', 'direction',
                           'dir', 'side', 'normal', 'tangent', 'color', 'size',
                           'dimensions', 'rotation', 'scale', 'radius',
                           'polygon', 'floorPolygon', 'deckUnionPolygon',
                           'crown', 'crownStairs', 'cloudSea', 'boosterPumps'))


def altitude(z):
    """C1-continuous, strictly increasing source-height map (scalar or array)."""
    value = np.asarray(z, dtype=float)
    t = np.clip((value-GROUND_UNCHANGED_THROUGH) /
                (TRANSLATION_START-GROUND_UNCHANGED_THROUGH), 0., 1.)
    result = value+ALLEY_LIFT*t*t*(3.-2.*t)
    return float(result) if result.ndim == 0 else result


def inverse_altitude(z):
    """Numerical inverse for frame/route authoring; deterministic to <1e-10 m."""
    values = np.asarray(z, dtype=float)
    low, high = values-ALLEY_LIFT, values.copy()
    for _ in range(48):
        middle = (low+high)*.5
        lower = altitude(middle) < values
        low = np.where(lower, middle, low)
        high = np.where(lower, high, middle)
    result = np.where(values <= GROUND_UNCHANGED_THROUGH, values,
                      np.where(values >= TRANSLATION_START+ALLEY_LIFT,
                               values-ALLEY_LIFT, (low+high)*.5))
    return float(result) if result.ndim == 0 else result


def _retile_tube_rings(old, new, uv):
    """Keep metre-based bark V repeat by remeasuring each tube centerline.

    Geometry.tube emits equal-V rings, a duplicated seam, then two cap vertices.
    Isolate each tube so the main trunk and roots never share a phase accumulator.
    End-cap UVs are intentionally preserved.
    """
    boundaries = np.r_[0, np.flatnonzero(np.abs(np.diff(uv[:, 1])) > 1e-9)+1, len(uv)]
    last = None
    accumulated = 0.
    changed = 0
    for lo, hi in zip(boundaries, boundaries[1:]):
        n = hi-lo
        if n < 5 or abs(uv[lo, 0]) > 1e-8 or uv[hi-1, 0] <= 0:
            last = None
            continue
        old_center = old[lo:hi-1].mean(axis=0)
        new_center = new[lo:hi-1].mean(axis=0)
        old_v = float(uv[lo, 1])
        if last is None or old_v <= last[2] or n != last[3]:
            accumulated = old_v
        else:
            # Preserve exact prior UV spacing when the segment only translates.
            old_length = np.linalg.norm(old_center-last[0])
            new_length = np.linalg.norm(new_center-last[1])
            accumulated += (old_v-last[2]) * new_length / max(old_length, 1e-12)
        if abs(accumulated-old_v) > 1e-7:
            uv[lo:hi, 1] = accumulated
            changed += n
        last = (old_center, new_center, old_v, n)
    return changed


def _retile_box_faces(old, new, faces, uv):
    """Remeasure independent Geometry.box faces in elongated lift timbers."""
    changed = 0
    # Each box face is two triangles with four unshared vertices.
    for f0, f1 in zip(faces[0::2], faces[1::2]):
        k = int(f0[0])
        if list(f0) != [k, k+1, k+2] or list(f1) != [k, k+2, k+3]:
            continue
        if k+3 >= len(uv):
            continue
        a = uv[k:k+4]
        u, v = a[1, 0], a[3, 1]
        if u <= 0 or v <= 0 or not np.allclose(a, [[0, 0], [u, 0], [u, v], [0, v]], atol=1e-8):
            continue
        new_u = u*np.linalg.norm(new[k+1]-new[k])/max(np.linalg.norm(old[k+1]-old[k]), 1e-12)
        new_v = v*np.linalg.norm(new[k+3]-new[k])/max(np.linalg.norm(old[k+3]-old[k]), 1e-12)
        if abs(new_u-u)+abs(new_v-v) > 1e-7:
            uv[k:k+4] = [[0, 0], [new_u, 0], [new_u, new_v], [0, new_v]]
            changed += 4
    return changed


def _transform_geometry(geometry, exclude_prefixes):
    if geometry is None:
        return {'transformedBatches': 0, 'transformedVertices': 0, 'retiledVertices': 0}
    if getattr(geometry, '_altitude_profile_id', None):
        raise ValueError('Altitude profile already applied to this Geometry')
    stats = {'transformedBatches': 0, 'transformedVertices': 0,
             'retiledVertices': 0, 'excludedBatches': 0}
    for (group, material), batch in geometry.batches.items():
        if any(group == p.rstrip('/') or group.startswith(p) for p in exclude_prefixes):
            stats['excludedBatches'] += 1
            continue
        old = np.asarray(batch['v'], dtype=float)
        if not len(old):
            continue
        if not np.isfinite(old).all():
            raise ValueError('Non-finite input geometry in '+group)
        new = old.copy()
        new[:, 2] = altitude(old[:, 2])
        uv = np.asarray(batch['uv'], dtype=float).copy()
        if group.startswith('Tree/') and material == 'Bark':
            stats['retiledVertices'] += _retile_tube_rings(old, new, uv)
        elif group == 'Lift' or group.startswith('Lift/'):
            stats['retiledVertices'] += _retile_box_faces(old, new, batch['f'], uv)
        # Keep the authoring list contract: later Geometry.add still works.
        batch['v'] = new.tolist()
        batch['uv'] = uv.tolist()
        stats['transformedBatches'] += 1
        stats['transformedVertices'] += int(np.count_nonzero(new[:, 2] != old[:, 2]))
    geometry._altitude_profile_id = PROFILE_ID
    return stats


class _MetadataTransform:
    """Explicit semantic fields plus identity memoization, never length-only guessing."""
    def __init__(self):
        self.seen = set()
        self.vectors = {}
        self.positions = 0
        self.boxes = 0

    def position(self, value):
        if not isinstance(value, (list, tuple, np.ndarray)) or len(value) != 3:
            return value
        if not all(isinstance(x, (int, float, np.number)) for x in value):
            return value
        if id(value) in self.vectors:
            return self.vectors[id(value)]
        p = [float(value[0]), float(value[1]), altitude(value[2])]
        if isinstance(value, list):
            value[:] = p
            p = value
        elif isinstance(value, np.ndarray):
            value[:] = p
            p = value
        else:
            p = tuple(p)
        self.vectors[id(value)] = p
        self.positions += 1
        return p

    def box(self, obj):
        """Preserve horizontal dimensions; map the actual top and bottom extents."""
        center = np.asarray(obj['center'], dtype=float).copy()
        size = np.asarray(obj['size'], dtype=float).copy()
        axes = np.asarray(obj.get('axes', np.eye(3)), dtype=float).reshape(3, 3)
        vertical = np.flatnonzero(np.abs(axes[:, 2]) > 1.-1e-7)
        if not len(vertical):
            half_z = np.sum(np.abs(axes[:, 2])*size)*.5
            bottom, top = center[2]-half_z, center[2]+half_z
            # A tilted OBB is exact only in an untranslated or rigidly moved zone.
            if bottom < TRANSLATION_START and top > GROUND_UNCHANGED_THROUGH:
                raise ValueError('Nonlinear altitude transform needs an upright BoxCollider: '+str(obj.get('name', 'unnamed')))
            obj['center'] = self.position(obj['center'])
            return
        axis = int(vertical[0])
        bottom, top = center[2]-size[axis]*.5, center[2]+size[axis]*.5
        mapped_bottom, mapped_top = altitude(bottom), altitude(top)
        adjusted = self.position(obj['center'])
        if isinstance(adjusted, tuple):
            adjusted = list(adjusted)
            obj['center'] = adjusted
        adjusted[2] = (mapped_bottom+mapped_top)*.5
        size[axis] = mapped_top-mapped_bottom
        # Protect independently shared size lists by replacing, never mutating.
        obj['size'] = size.tolist()
        self.boxes += 1

    def walk(self, value, key=None):
        if key in UNTOUCHED_KEYS:
            return value
        if key in POSITION_KEYS:
            return self.position(value)
        if isinstance(value, dict):
            if id(value) in self.seen:
                return value
            self.seen.add(id(value))
            is_box = 'center' in value and 'size' in value and ('axes' in value or key == 'solidBoxes')
            if is_box:
                self.box(value)
            for child_key, child in list(value.items()):
                if is_box and child_key in ('center', 'size', 'axes'):
                    continue
                if child_key in HEIGHT_KEYS and isinstance(child, (int, float, np.number)):
                    value[child_key] = altitude(child)
                elif child_key == 'levels' and isinstance(child, dict):
                    if id(child) not in self.seen:
                        self.seen.add(id(child))
                        for level, z in list(child.items()):
                            child[level] = altitude(z)
                else:
                    value[child_key] = self.walk(child, child_key)
            return value
        if isinstance(value, list):
            if id(value) in self.seen:
                return value
            self.seen.add(id(value))
            for i, child in enumerate(value):
                if key in POINT_LIST_KEYS and isinstance(child, (list, tuple, np.ndarray)) and len(child) == 3:
                    value[i] = self.position(child)
                else:
                    value[i] = self.walk(child, key)
            return value
        return value


def apply_altitude_profile(g, c, metadata, *, exclude_prefixes=('Landscape/', 'Crown/', 'Safety/Crown/', 'Ramps/Crown', 'Floors/Crown', 'Infrastructure/Boosters/')):
    """Transform legacy g/c and supplied metadata IN PLACE, and return a report.

    metadata: dict(levels, stairs, spawns, lights, steam, stations, teleports,
    solidBoxes, floorTests, wallTests, guards, routes, infrastructure, stage).
    Nested stage/infrastructure records can share objects with outer lists.
    Geometry and metadata carry one-shot markers; a second invocation raises.
    WKT/XY floor polygons, directions, colors, sizes and ordinary scalar tuning
    values are unchanged, except upright BoxCollider vertical extent.
    """
    if metadata.get('_altitudeProfileApplied'):
        raise ValueError('Altitude profile already applied to this metadata')
    for geometry in (g, c):
        if geometry is not None and getattr(geometry, '_altitude_profile_id', None):
            raise ValueError('Altitude profile already applied to this Geometry')
    transform = _MetadataTransform()
    transform.walk(metadata)
    visuals = _transform_geometry(g, exclude_prefixes)
    collision = _transform_geometry(c, exclude_prefixes)
    metadata['_altitudeProfileApplied'] = PROFILE_ID
    stage = metadata.get('stage') or metadata.get('nohStage')
    if stage:
        stage['notes'] = [note.replace('collider at Z40', 'collider at Z140')
                          for note in stage.get('notes', [])]
    return {'id': PROFILE_ID, 'sourceCoordinates': 'XYZ, Z up, metres',
            'addedAlleyHeight': ALLEY_LIFT,
            'groundUnchangedThrough': GROUND_UNCHANGED_THROUGH,
            'translationStartsAtOriginalZ': TRANSLATION_START,
            'levels': dict(metadata.get('levels', {})),
            'visuals': visuals, 'collision': collision,
            'metadataPositions': transform.positions, 'boxColliders': transform.boxes,
            'excludedPrefixes': list(exclude_prefixes),
            'independentNewStairsMustBeAddedAfterward': True}


def self_test():
    """Small deterministic regression suite; never regenerates the main world."""
    from world_geometry import Geometry
    checks = {}
    z = np.linspace(-30, 230, 30001)
    checks['strictly_monotone'] = bool(np.all(np.diff(altitude(z)) > 0))
    checks['continuous_at_joins'] = all(abs(altitude(p+1e-7)-altitude(p-1e-7)) < 3e-7 for p in (14., 33.))
    checks['inverse_round_trip'] = bool(np.max(abs(inverse_altitude(altitude(z))-z)) < 1e-9)
    g, c = Geometry(), Geometry()
    g.material('Bark', [1, 1, 1]); c.material('collision', [1, 1, 1])
    g.group = 'Tree/Trunk'; g.tube([[0, 0, 0], [0, 0, 14], [0, 0, 24], [0, 0, 33], [0, 0, 119]], [1]*5, 'Bark', 8)
    g.group = 'Landscape/Test'; g.box([2, 3, 22], [1, 2, 3], 'Bark')
    g.group = 'Lift'; g.box([0, 0, 23.7], [.27, .27, 47.4], 'Bark')
    g.group = 'Crown/Test'; g.box([0, 0, 200], [4, 5, 3], 'Bark')
    g.group = 'Shops/Test'; g.box([0, 0, 42], [4, 5, 3], 'Bark')
    c.group = 'Floors/L2'; c.box([0, 0, 39.8], [10, 10, .4], 'collision')
    original = copy.deepcopy(g.batches)
    shared_position = [0, 0, 40.]
    shared_test = {'position': shared_position, 'id': 'same'}
    post = {'center': [3, 4, 41.43], 'size': [.23, .23, 2.86], 'axes': np.eye(3).reshape(-1).tolist()}
    tall = {'center': [0, 0, 23.7], 'size': [.27, .27, 47.4], 'axes': np.eye(3).reshape(-1).tolist()}
    light = {'position': [1, 2, 43], 'color': [1, .7, .2], 'range': 4.}
    meta = {'levels': {'G0': 0, 'L1': 34, 'L2': 40, 'L3': 46, 'L4': 52},
            'crownStairs': {'center': [0, 0, 212], 'groundZ': 0.},
            'spawns': [[0, 0, 34.08]], 'lights': [light], 'solidBoxes': [post, tall],
            'floorTests': [shared_test], 'stage': {'z': 40, 'center': shared_position,
            'front': [0, 0, 1], 'solidBoxes': [post], 'floorTests': [shared_test],
            'visualBounds': {'min': [0, 0, 39], 'max': [2, 3, 44]},
            'floorRecommendation': {'z': 40, 'polygon': [[0, 0], [0, 1], [1, 1]]}},
            'infrastructure': {'lights': [light], 'utilityRoutes': [
            {'id': 'Ground_water', 'points': [[0, 0, 1.3], [2, 3, 1.3]]},
            {'id': 'Trunk_water', 'points': [[2, 3, 1.3], [3, 4, 52]]}]},
            'guards': [{'a': [0, 0], 'b': [1, 2], 'base': 40, 'top': 48, 'thickness': .24}]}
    report = apply_altitude_profile(g, c, meta)
    checks['exact_levels'] = meta['levels'] == {'G0': 0, 'L1': 134, 'L2': 140, 'L3': 146, 'L4': 152}
    checks['shared_objects_once'] = shared_position[2] == 140 and light['position'][2] == 143 and post['center'][2] == 141.43
    checks['directions_colors_dimensions'] = meta['stage']['front'] == [0, 0, 1] and light['color'] == [1, .7, .2] and np.allclose(post['size'], [.23, .23, 2.86])
    checks['tall_box_extents'] = np.allclose(tall['center'], [0, 0, 73.7]) and np.allclose(tall['size'], [.27, .27, 147.4])
    checks['new_crown_unchanged'] = g.batches[('Crown/Test', 'Bark')] == original[('Crown/Test', 'Bark')] and meta['crownStairs']['center'][2] == 212
    checks['landscape_unchanged'] = g.batches[('Landscape/Test', 'Bark')] == original[('Landscape/Test', 'Bark')]
    a, b = np.asarray(original[('Shops/Test', 'Bark')]['v']), np.asarray(g.batches[('Shops/Test', 'Bark')]['v'])
    checks['shop_dimensions_unchanged'] = np.allclose(b-a, [0, 0, 100])
    routes = meta['infrastructure']['utilityRoutes']
    checks['route_endpoints_coincide'] = routes[0]['points'][-1] == routes[1]['points'][0]
    checks['finite_geometry'] = all(np.isfinite(v).all() for geom in (g, c) for batch in geom.batches.values() for v in (np.asarray(batch['v']), np.asarray(batch['uv'])))
    checks['bark_and_lift_repeat'] = report['visuals']['retiledVertices'] > 0 and abs(max(u[1] for u in g.batches[('Tree/Trunk', 'Bark')]['uv'])-219.) < 1e-8
    try:
        apply_altitude_profile(g, c, meta)
        checks['double_application_rejected'] = False
    except ValueError:
        checks['double_application_rejected'] = True
    return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks}


if __name__ == '__main__':
    import json
    result = self_test()
    print(json.dumps(result, indent=2))
    raise SystemExit(result['status'] != 'PASS')
