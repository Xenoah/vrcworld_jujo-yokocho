"""Independent offline whole-world crown-route collider regression.

Reads the final binary collider payload and manifest, never the authoring module.
This is geometric validation, not Unity CharacterController/VRChat simulation.
Run: python Source/validate_crown.py [project_root]
"""
from __future__ import annotations

import json
import math
import struct
import sys
import time
from pathlib import Path

import numpy as np
from shapely import wkt
from shapely.geometry import LineString, MultiPoint, Point
from shapely.strtree import STRtree

RADIUS = .25
BODY_HEIGHT = 1.65
HEADROOM = 2.20
SWEEP_STEP = .20
EPS = 2e-5


class Report:
    def __init__(self):
        self.checks = []
        self.failures = []

    def check(self, name, passed, detail=None):
        row = {'name': name, 'passed': bool(passed)}
        if detail is not None:
            row['detail'] = detail
        self.checks.append(row)
        if not passed:
            self.failures.append(row)


def read_collision(path):
    """Read actual JYWM source-coordinate triangles; reject partial files."""
    def exact(stream, size):
        data = stream.read(size)
        if len(data) != size:
            raise ValueError('Truncated collision payload')
        return data

    meshes = []
    with path.open('rb') as stream:
        if exact(stream, 4) != b'JYWM':
            raise ValueError('Invalid collision payload signature')
        version, count = struct.unpack('<II', exact(stream, 8))
        if version != 1:
            raise ValueError(f'Unsupported collision payload version {version}')
        for _ in range(count):
            names = [exact(stream, struct.unpack('<I', exact(stream, 4))[0]).decode()
                     for _ in range(2)]
            nv, ni = struct.unpack('<II', exact(stream, 8))
            if ni % 3:
                raise ValueError(f'Non-triangular index count in {names[0]}')
            vertices = np.frombuffer(exact(stream, nv * 12), '<f4').reshape(-1, 3).astype(float)
            exact(stream, nv * 8)  # UVs
            exact(stream, nv * 4)  # Color bytes
            faces = np.frombuffer(exact(stream, ni * 4), '<u4').reshape(-1, 3)
            if not np.isfinite(vertices).all() or (ni and int(faces.max()) >= nv):
                raise ValueError(f'Invalid vertices/indices in {names[0]}')
            meshes.append({'group': names[0], 'material': names[1],
                           'vertices': vertices, 'faces': faces,
                           'triangles': vertices[faces]})
        if stream.read(1):
            raise ValueError('Unexpected trailing bytes in collision payload')
    return meshes


class Rays:
    def __init__(self, triangles):
        tri = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
        self.a = tri[:, 0]
        self.e1 = tri[:, 1] - tri[:, 0]
        self.e2 = tri[:, 2] - tri[:, 0]
        self.lo = tri.min(axis=1) - EPS
        self.hi = tri.max(axis=1) + EPS

    def hit(self, origin, direction, limit):
        """Front-facing Moller-Trumbore, matching default Unity ray winding."""
        o, d = np.asarray(origin), np.asarray(direction)
        end = o + d * limit
        low, high = np.minimum(o, end) - EPS, np.maximum(o, end) + EPS
        ids = np.where(np.all((self.lo <= high) & (self.hi >= low), axis=1))[0]
        if not len(ids):
            return None
        a, e1, e2 = self.a[ids], self.e1[ids], self.e2[ids]
        h = np.cross(np.broadcast_to(d, e2.shape), e2)
        det = np.einsum('ij,ij->i', e1, h)
        good = det > 1e-8
        inv = np.divide(1., det, out=np.zeros_like(det), where=good)
        s = o - a
        u = inv * np.einsum('ij,ij->i', s, h)
        q = np.cross(s, e1)
        v = inv * np.einsum('j,ij->i', d, q)
        t = inv * np.einsum('ij,ij->i', e2, q)
        good &= ((u >= -EPS) & (v >= -EPS) & (u + v <= 1 + EPS) &
                 (t >= -EPS) & (t <= limit + EPS))
        return float(t[good].min()) if good.any() else None


def clipped_projection(triangles, low, high):
    """XY projection after clipping a convex solid/triangle to a Z interval.

    Working on each individual prism avoids incorrectly filling the interior of
    a closed guard perimeter. The projected convex hull is exact for these
    convex eight-corner wall/box primitives.
    """
    tri = np.asarray(triangles)
    points = tri.reshape(-1, 3)
    keep = points[(points[:, 2] >= low - EPS) & (points[:, 2] <= high + EPS)]
    found = [keep]
    a = tri.reshape(-1, 3)
    b = np.roll(tri, -1, axis=1).reshape(-1, 3)
    dz = b[:, 2] - a[:, 2]
    for z in (low, high):
        mask = ((np.minimum(a[:, 2], b[:, 2]) <= z + EPS) &
                (np.maximum(a[:, 2], b[:, 2]) >= z - EPS) & (np.abs(dz) > 1e-10))
        if mask.any():
            t = np.clip((z - a[mask, 2]) / dz[mask], 0., 1.)
            found.append(a[mask] + (b[mask] - a[mask]) * t[:, None])
    points = np.concatenate(found)
    if not len(points):
        return None
    return MultiPoint(points[:, :2]).convex_hull


def box_triangles(box):
    center = np.asarray(box['center'], dtype=float)
    sizes = np.asarray(box['size'], dtype=float)
    axes = np.asarray(box['axes'], dtype=float).reshape(3, 3)
    signs = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]])
    vertices = (signs * sizes / 2) @ axes + center
    faces = np.array([(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
                      (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
                      (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)])
    return vertices[faces]


class Solids:
    def __init__(self, records):
        self.records = records
        self.projections = [MultiPoint(r['triangles'].reshape(-1, 3)[:, :2]).convex_hull
                            for r in records]
        self.tree = STRtree(self.projections)
        self.low = np.array([r['triangles'][:, :, 2].min() for r in records])
        self.high = np.array([r['triangles'][:, :, 2].max() for r in records])

    def intersections(self, footprint, low, high):
        found = []
        for i in self.tree.query(footprint):
            if self.high[i] < low - EPS or self.low[i] > high + EPS:
                continue
            geom = clipped_projection(self.records[i]['triangles'], low, high)
            if geom is not None and footprint.intersects(geom):
                found.append(self.records[i]['name'])
        return found


def densified_segments(points):
    for a, b in zip(points, points[1:]):
        count = max(1, int(math.ceil(np.linalg.norm(b - a) / SWEEP_STEP)))
        for j in range(count):
            yield a + (b - a) * j / count, a + (b - a) * (j + 1) / count


def validate(root, report):
    manifest_path = root / 'Assets/TreeTopYokocho/Data/WorldManifest.json'
    manifest = json.loads(manifest_path.read_text())
    crown = manifest.get('crownStairs')
    report.check('Integrated crownStairs metadata exists', isinstance(crown, dict) and bool(crown.get('routes')))
    if not isinstance(crown, dict) or not crown.get('routes'):
        return {'manifest': str(manifest_path), 'integrated': False}
    meshes = read_collision(root / 'Assets/TreeTopYokocho/Data/CollisionMeshes.bytes')
    floors, walls, obstacles, floor_records = [], [], [], []
    bad_format, legacy_walls, crown_walls = [], 0, 0
    for mesh in meshes:
        name, tri = mesh['group'], mesh['triangles']
        if name.startswith(('Floors/', 'Ramps/')):
            floors.extend(tri)
            floor_records.extend({'name': f'{name} triangle {i}', 'triangles': x[None]}
                                 for i, x in enumerate(tri))
        elif name.startswith('Safety/'):
            walls.extend(tri)
            if len(tri) % 12:
                bad_format.append(name)
                obstacles.extend({'name': f'{name} triangle {i}', 'triangles': x[None]}
                                 for i, x in enumerate(tri))
            else:
                for i in range(0, len(tri), 12):
                    chunk = tri[i:i + 12]
                    corners = np.unique(np.round(chunk.reshape(-1, 3), 5), axis=0)
                    if len(corners) != 8:
                        bad_format.append(f'{name} primitive {i // 12}: {len(corners)} corners')
                    obstacles.append({'name': f'{name} prism {i // 12}', 'triangles': chunk})
                    if name.startswith('Safety/Crown'):
                        crown_walls += 1
                    else:
                        legacy_walls += 1
        else:
            # Do not silently omit additional physical collision groups.
            obstacles.extend({'name': f'{name} triangle {i}', 'triangles': x[None]}
                             for i, x in enumerate(tri))
    for box in manifest.get('solidBoxes', []):
        obstacles.append({'name': 'solidBoxes/' + box['name'], 'triangles': box_triangles(box)})
    report.check('Safety primitives have 12 triangles / 8 corners', not bad_format, bad_format[:20])
    report.check('Both legacy and crown safety meshes included', legacy_walls > 0 and crown_walls > 0,
                 {'legacyPrisms': legacy_walls, 'crownPrisms': crown_walls})
    report.check('Actual floor and ramp triangles loaded', len(floors) > 0, len(floors))
    if not floors:
        return {'integrated': True, 'meshCount': len(meshes)}
    floor_rays, wall_rays = Rays(floors), Rays(walls)
    solids, floor_solids = Solids(obstacles), Solids(floor_records)
    routes = []
    bad_routes = []
    for row in crown['routes']:
        points = np.asarray(row.get('points', []), dtype=float)
        valid = points.ndim == 2 and points.shape[1:] == (3,) and len(points) >= 2 and np.isfinite(points).all()
        if not valid:
            bad_routes.append(row.get('name', '<unnamed>'))
            continue
        gap = float(np.linalg.norm(np.diff(points, axis=0), axis=1).max())
        if gap > .50001:
            bad_routes.append(f"{row['name']}: {gap:.5f} m sample gap")
        routes.append((row['name'], points))
    report.check('Authoritative routes finite, complete and sampled at <=0.5m', not bad_routes, bad_routes[:20])
    by_name = dict(routes)
    needed = {'CrownGroundApproach', 'CrownHelix', 'CrownArrivalBridge', 'CrownLookoutBridge', 'CrownObservatory'}
    report.check('All five required route branches recorded', needed.issubset(by_name), sorted(by_name))
    if not needed.issubset(by_name):
        return {'integrated': True, 'meshCount': len(meshes), 'routeCount': len(routes)}

    center_misses, edge_misses, body_hits, overhead_hits = [], [], [], []
    sample_count, edge_count, sweep_count = 0, 0, 0
    directions = [np.array([math.cos(a), math.sin(a), 0.]) * RADIUS
                  for a in np.linspace(0., math.tau, 8, endpoint=False)]
    for name, points in routes:
        for p in points:
            sample_count += 1
            hit = floor_rays.hit(p + [0., 0., .75], [0., 0., -1.], 1.5)
            if hit is None or abs(hit - .75) > .035:
                center_misses.append({'route': name, 'position': p.tolist(), 'distance': hit})
            # Eight foot-support spokes every second authoritative station.
            # Their expected Z can vary across a legitimate sloping ramp.
            if sample_count % 2 == 0:
                for offset in directions:
                    edge_count += 1
                    hit = floor_rays.hit(p + offset + [0., 0., .75], [0., 0., -1.], 1.5)
                    if hit is None or abs(hit - .75) > .27:
                        edge_misses.append({'route': name, 'position': (p + offset).tolist(), 'distance': hit})
        for a, b in densified_segments(points):
            sweep_count += 1
            footprint = LineString([a[:2], b[:2]]).buffer(RADIUS, quad_segs=8)
            lower, upper = min(a[2], b[2]), max(a[2], b[2])
            hits = solids.intersections(footprint, lower + .055, upper + BODY_HEIGHT)
            if hits:
                body_hits.append({'route': name, 'start': a.tolist(), 'end': b.tolist(), 'obstacles': hits[:8]})
            # Check remaining space above the body against actual guard/prop
            # solids, then against actual slabs, including their undersides.
            hits = solids.intersections(footprint, lower + BODY_HEIGHT, upper + HEADROOM)
            slab_hits = floor_solids.intersections(footprint, lower + .32, upper + HEADROOM)
            if hits or slab_hits:
                overhead_hits.append({'route': name, 'start': a.tolist(), 'end': b.tolist(),
                                      'obstacles': (hits + slab_hits)[:8]})
    report.check('Front-facing center floors match route elevation', not center_misses,
                 {'probes': sample_count, 'misses': center_misses[:30], 'missCount': len(center_misses)})
    report.check('Radius0.25m floor support around route centers', not edge_misses,
                 {'probes': edge_count, 'misses': edge_misses[:30], 'missCount': len(edge_misses)})
    report.check('Radius0.25m / height1.65m continuous route sweep clears all obstacles', not body_hits,
                 {'sweptSegments': sweep_count, 'hits': body_hits[:40], 'hitCount': len(body_hits)})
    report.check('All route sweeps retain >=2.2m overhead space', not overhead_hits,
                 {'sweptSegments': sweep_count, 'hits': overhead_hits[:40], 'hitCount': len(overhead_hits)})

    # Check the emitted front-facing guard rays against ALL actual Safety groups.
    wall_tests = manifest.get('wallTests', [])
    if not any(x.get('group', '').startswith('Safety/Crown') for x in wall_tests):
        wall_tests = [*wall_tests, *crown.get('wallTests', [])]
    missed = []
    for i, test in enumerate(wall_tests):
        a, b = np.asarray(test['start']), np.asarray(test['end'])
        delta = b - a
        length = np.linalg.norm(delta)
        if length < EPS or wall_rays.hit(a, delta / max(length, EPS), length) is None:
            missed.append({'index': i, 'id': test.get('id'), 'start': a.tolist(), 'end': b.tolist()})
    report.check('Front-facing guard rays hit actual integrated walls', not missed,
                 {'rays': len(wall_tests), 'misses': missed[:30], 'missCount': len(missed)})

    emitted_floor_misses = []
    for test in crown.get('floorTests', []):
        p = np.asarray(test['position'])
        hit = floor_rays.hit(p + [0., 0., .75], [0., 0., -1.], 1.65)
        if hit is None or abs(hit - .75) > .04:
            emitted_floor_misses.append({'id': test.get('id'), 'position': p.tolist(), 'distance': hit})
    report.check('All emitted crown floor probes hit integrated slabs', not emitted_floor_misses,
                 {'probes': len(crown.get('floorTests', [])), 'misses': emitted_floor_misses[:30],
                  'missCount': len(emitted_floor_misses)})

    main = crown.get('route', {})
    ascent = np.asarray(main.get('mainAscentSamples', []), dtype=float)
    ascent_ok = (ascent.ndim == 2 and ascent.shape[1:] == (3,) and len(ascent) > 10
                 and np.isfinite(ascent).all())
    expected_ascent = np.vstack([by_name['CrownGroundApproach'],
                                 by_name['CrownHelix'][1:], by_name['CrownObservatory'][1:]])
    expected_crown_z = 212. if manifest.get('features', {}).get('high_altitude') else 112.
    if ascent_ok:
        ascent_ok = (ascent.shape == expected_ascent.shape
                     and np.allclose(ascent, expected_ascent, atol=1e-6, rtol=0.)
                     and np.linalg.norm(ascent[0] - by_name['CrownGroundApproach'][0]) < .02
                     and abs(ascent[-1, 2] - expected_crown_z) < .02
                     and np.linalg.norm(np.diff(ascent, axis=0), axis=1).max() <= .50001
                     and np.diff(ascent[:, 2]).min() >= -.001)
    report.check(f'Complete ground-to-Z{expected_crown_z:g} ascent is continuous and reversible', ascent_ok,
                 {'samples': len(ascent), 'usesTeleport': False})
    joins = [
        ('Ground/helix', by_name['CrownGroundApproach'][-1], by_name['CrownHelix'][0]),
        ('Helix/observatory', by_name['CrownHelix'][-1], by_name['CrownObservatory'][0]),
    ]
    join_errors = [{'join': name, 'gap': float(np.linalg.norm(a - b))}
                   for name, a, b in joins if np.linalg.norm(a - b) > .02]
    for name in ('CrownArrivalBridge', 'CrownLookoutBridge'):
        endpoint = by_name[name][0]
        gap = np.linalg.norm(by_name['CrownHelix'] - endpoint, axis=1).min()
        if gap > .02:
            join_errors.append({'join': name + '/helix', 'gap': float(gap)})
    legacy_floors = {row['level']: wkt.loads(row['wkt']) for row in manifest['floors']}
    for name, level, endpoint in (
            ('Ground/legacy G0', 'G0', by_name['CrownGroundApproach'][0]),
            ('Arrival/legacy L1', 'L1', by_name['CrownArrivalBridge'][-1]),
            ('Lookout/legacy L4', 'L4', by_name['CrownLookoutBridge'][-1])):
        if not legacy_floors[level].buffer(EPS).covers(Point(endpoint[:2]).buffer(RADIUS, quad_segs=8)):
            join_errors.append({'join': name, 'problem': 'avatar footprint not fully on legacy slab'})
    report.check('All route joins and three legacy floor attachments overlap safely', not join_errors, join_errors)
    return {'integrated': True, 'meshCount': len(meshes), 'routeCount': len(routes),
            'routeSamples': sample_count, 'supportProbes': sample_count + edge_count,
            'sweptSegments': sweep_count, 'guardRays': len(wall_tests),
            'solidBoxes': len(manifest.get('solidBoxes', [])),
            'legacySafetyPrisms': legacy_walls, 'crownSafetyPrisms': crown_walls,
            'floorTriangles': len(floors), 'safetyTriangles': len(walls)}


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    started, report, counts = time.time(), Report(), {}
    try:
        counts = validate(root, report)
    except Exception as error:
        report.check('Verifier completed without invalid/missing input', False,
                     f'{type(error).__name__}: {error}')
    result = {
        'status': 'PASS' if not report.failures else 'FAIL',
        'scope': 'Independent offline integrated-mesh geometry verification; NOT Unity physics, CharacterController, Udon or VRChat runtime simulation.',
        'assumptions': {'sourceCoordinates': 'XYZ_Z_UP', 'avatarRadius': RADIUS,
                        'standingBodyHeight': BODY_HEIGHT, 'minimumOverheadClearance': HEADROOM,
                        'maximumSweepStep': SWEEP_STEP, 'frontFacingFloorRays': True,
                        'stepCollisionMode': 'continuous ramp',
                        'floorSlopeAllowance': 'Eight radius0.25m support spokes may vary +/-0.27m; center floor must match within0.035m',
                        'sweepModel': 'Conservative swept vertical cylinder; convex wall/box solids are clipped in Z before projection'},
        'checks': report.checks, 'failures': report.failures,
        'counts': counts, 'elapsedSeconds': round(time.time() - started, 3),
        'unityExecuted': False, 'vrchatExecuted': False,
    }
    destination = root / 'Docs/crown_validation.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'counts': counts,
                      'failedChecks': [x['name'] for x in report.failures],
                      'elapsedSeconds': result['elapsedSeconds'], 'report': str(destination)}, indent=2))
    return 0 if not report.failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
