"""Continuous ground-to-crown circulation for TreeTopYokocho (source XYZ, Z up).

The walking collider is a closed swept ramp, not 700 separate step colliders.
Visual treads, railings, lamps, wiring and brackets are independently batched.
See Docs/CrownStairs.md for integration and validation contracts.
"""
from __future__ import annotations

import math
import numpy as np
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union

UP = np.array([0., 0., 1.])
WIDTH = 2.8
CROWN_Z = 112.0
BARRIER_HEIGHT = 8.0
BARRIER_THICKNESS = .24
# Every wall primitive has exactly these twelve consecutive outward triangles.
PRISM_FACES = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
               (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2),
               (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]


def _lengths(points):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def _resample(points, maximum=.44):
    """Preserve every original corner and bound every 3D segment length."""
    out = [np.asarray(points[0], dtype=float)]
    for a, b in zip(points, points[1:]):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / maximum)))
        out.extend(a + (b - a) * j / n for j in range(1, n + 1))
    return np.asarray(out)


def _offsets(points, half):
    """XY miter joins. Vertical elevation does not reduce the clear width."""
    points = np.asarray(points)
    directions = np.diff(points[:, :2], axis=0)
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    normals = np.column_stack([-directions[:, 1], directions[:, 0]])
    out = []
    for i in range(len(points)):
        if i == 0:
            off = normals[0] * half
        elif i == len(points) - 1:
            off = normals[-1] * half
        else:
            bisect = normals[i - 1] + normals[i]
            bisect /= np.linalg.norm(bisect)
            off = bisect * half / max(.4, float(np.dot(bisect, normals[i])))
        out.append([off[0], off[1], 0.])
    return np.asarray(out)


def _footprint(points, width):
    p = np.asarray(points)
    off = _offsets(p, width / 2)
    return Polygon(np.vstack([(p + off)[:, :2], (p - off)[::-1, :2]])).buffer(0)


def _strip_mesh(points, width, thickness=.30, top_offset=0., offsets=None):
    """Closed swept strip with shared vertices and positive top winding."""
    p = np.asarray(points, dtype=float) + UP * top_offset
    off = _offsets(p, width / 2) if offsets is None else np.asarray(offsets)
    vertices = []
    for a, d in zip(p, off):
        vertices.extend([a + d, a - d, a + d - UP * thickness,
                         a - d - UP * thickness])
    faces = []
    for i in range(len(p) - 1):
        k, n = i * 4, (i + 1) * 4
        faces.extend([(k, k + 1, n + 1), (k, n + 1, n),
                      (k + 2, n + 3, k + 3), (k + 2, n + 2, n + 3),
                      (k, n, n + 2), (k, n + 2, k + 2),
                      (k + 1, k + 3, n + 3), (k + 1, n + 3, n + 1)])
    last = 4 * (len(p) - 1)
    faces.extend([(0, 2, 3), (0, 3, 1),
                  (last, last + 1, last + 3), (last, last + 3, last + 2)])
    return np.asarray(vertices), np.asarray(faces, dtype=np.int32)


def _prism(a, b, width=.24, base=-.35, top=8.):
    """Eight corners, twelve outward triangles, compatible with Safety slicers."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    d = b - a
    left = np.array([-d[1], d[0], 0.])
    left *= width / (2 * np.linalg.norm(left))
    # PRISM_FACES expects the upper four corners first, in CCW order.
    v = [a + left + UP * top, a - left + UP * top,
         b - left + UP * top, b + left + UP * top,
         a + left + UP * base, a - left + UP * base,
         b - left + UP * base, b + left + UP * base]
    return np.asarray(v), PRISM_FACES


def _helix_height(t):
    """Two full-width flat landings, joined with moderate catch-up gradients."""
    z = float(t)
    for h in (34., 52.):
        d = t - h
        if abs(d) <= .46:
            return h
        if abs(d) < 1.46:
            return h + math.copysign((abs(d) - .46) * 1.46, d)
    return z


def _helix_point(t):
    z = _helix_height(t)
    u = np.clip((z - 52.) / 60., 0., 1.)
    radius = 40. - 20. * (3 * u * u - 2 * u * u * u)
    a = math.radians(100. + 5. * t)
    return np.array([radius * math.cos(a), radius * math.sin(a), z])


def _parts(line):
    if line.is_empty:
        return []
    if line.geom_type == 'LineString':
        return [line]
    return [x for x in line.geoms if x.geom_type == 'LineString']


def crown_attachment_openings():
    """Call before legacy floor guard creation; contains no generated meshes.

    Suppress legacy safety AND visible railing where their edges intersect the
    relevant corridor. Floors remain unchanged. The corridor extends into each
    original slab, so round-avatar centers do not have to pass a point contact.
    """
    return [
        {'id': 'Crown_G0_Entry', 'level': 'G0', 'z': 0., 'width': 3.0,
         'centerline': [[-20., -29., 0.], [-31., -29., 0.]],
         'bounds': [-31.4, -30.65, -19.6, -27.35]},
        {'id': 'Crown_L1_Arrival', 'level': 'L1', 'z': 34., 'width': 3.0,
         'centerline': [[0., -40., 34.], [0., -32., 34.]],
         'bounds': [-1.65, -40.4, 1.65, -31.6]},
        {'id': 'Crown_L4_Lookout', 'level': 'L4', 'z': 52., 'width': 3.0,
         'centerline': [[44. * math.cos(math.radians(141.)),
                         44. * math.sin(math.radians(141.)), 52.],
                        [-28., 24., 52.]],
         'bounds': [-35.9, 22.3, -26.3, 29.4]},
    ]


def add_crown_stairs(g, c, M, rng):
    """Append the complete circulation asset and return manifest-ready records.

    Existing floor/guard batches are deliberately not altered. Integration must
    open the three legacy attachment corridors returned above. ``rng`` is
    accepted for the standard authoring interface; this module is deterministic.
    """
    del rng
    old_g, old_c = g.group, c.group
    before_v = sum(len(b['f']) for b in g.batches.values())
    before_c = sum(len(b['f']) for b in c.batches.values())
    lights, floor_tests, wall_tests, barriers, lamp_tests = [], [], [], [], []
    wire_runs, tread_sizes = [], []

    tt = sorted(set(np.linspace(0., 112., 1121).tolist() +
                    [32.54, 33.54, 34., 34.46, 35.46,
                     50.54, 51.54, 52., 52.46, 53.46]))
    helix = _resample([_helix_point(t) for t in tt])
    base = helix[0]
    # Approach from the west, then turn outside r44 and align with the first
    # stair tangent. A direct west-to-base line would cause a U-turn overlap.
    tangent = np.array([-math.sin(math.radians(100.)),
                         math.cos(math.radians(100.)), 0.])
    approach_end = base - tangent * 8.
    turn_center = approach_end - np.array([math.cos(math.radians(-80.)),
                                           math.sin(math.radians(-80.)), 0.]) * 7.
    turn = [turn_center + np.array([7. * math.cos(a), 7. * math.sin(a), 0.])
            for a in np.linspace(math.radians(90.), math.radians(-80.), 51)]
    ground = _resample([[-20., -29., 0.], [-31., -29., 0.],
                        [-46., -22., 0.], [-48., 8., 0.],
                        [-39., 34., 0.], [-23., 49., 0.],
                        [turn_center[0] - 10., turn_center[1] + 7., 0.],
                        *turn, base])
    arrival = _resample([[0., -40., 34.], [0., -32., 34.]])
    north_arc = [np.array([44. * math.cos(a), 44. * math.sin(a), 52.])
                 for a in np.linspace(0., math.radians(132.), 232)]
    corner = np.array([44. * math.cos(math.radians(141.)),
                       44. * math.sin(math.radians(141.)), 52.])
    end = np.array([-28., 24., 52.])
    direction = end - corner; direction /= np.linalg.norm(direction)
    curve_end = corner + direction * 4.4
    curve = [(1 - t) ** 2 * north_arc[-1] +
             2 * (1 - t) * t * corner + t * t * curve_end
             for t in np.linspace(0., 1., 41)[1:]]
    lookout = _resample([[40., 0., 52.], *north_arc, *curve, end])
    # The 55-degree notch is essential: a full annulus would put a slab across
    # the last ~8 vertical metres of the stair and its tall safety walls.
    crown = _resample([[20. * math.cos(a), 20. * math.sin(a), 112.]
                      for a in np.linspace(math.radians(300.),
                                           math.radians(605.), 247)])
    paths = [
        {'id': 'CrownGroundApproach', 'points': ground, 'width': 3., 'type': 'walkway'},
        {'id': 'CrownHelix', 'points': helix, 'width': WIDTH, 'type': 'stair'},
        {'id': 'CrownArrivalBridge', 'points': arrival, 'width': 3., 'type': 'bridge'},
        {'id': 'CrownLookoutBridge', 'points': lookout, 'width': 3., 'type': 'bridge'},
        {'id': 'CrownObservatory', 'points': crown, 'width': 6., 'type': 'observatory'},
    ]
    for path in paths:
        path['footprint'] = _footprint(path['points'], path['width'])
    main = paths[1]
    landing_masks = {}
    for z in (0., 34., 52., 112.):
        near = helix[np.abs(helix[:, 2] - z) < (.24 if z in (0., 112.) else .00001)]
        landing_masks[z] = _footprint(near, WIDTH) if len(near) > 1 else Point(_helix_point(z)[:2]).buffer(1.4)
    legacy = {'CrownGroundApproach': (0., box(-26., -37., -6., -21.)),
              'CrownArrivalBridge': (34., box(-10., -34., 10., -18.)),
              'CrownLookoutBridge': (52., box(-29.5, 18., -20.5, 26.))}

    def masks_for(path, a, b):
        h = (a[2] + b[2]) / 2
        result = []
        if path['id'] == 'CrownHelix':
            for z, idx in ((0., 0), (34., 2), (52., 3), (112., 4)):
                if abs(h - z) < .25:
                    result.append(paths[idx]['footprint'].buffer(.025))
        else:
            z = float(path['points'][0, 2])
            if z in landing_masks:
                result.append(landing_masks[z].buffer(.025))
            if path['id'] in legacy:
                result.append(legacy[path['id']][1].buffer(.035))
        return result

    def clipped_edges(path, a, b):
        line = LineString([a[:2], b[:2]])
        masks = masks_for(path, a, b)
        clipped = line.difference(unary_union(masks)) if masks else line
        dxy = b[:2] - a[:2]
        dd = float(dxy @ dxy)
        out = []
        for part in _parts(clipped):
            if part.length < .008:
                continue
            ends = []
            for xy in (part.coords[0], part.coords[-1]):
                t = float((np.asarray(xy) - a[:2]) @ dxy / dd)
                ends.append(a + np.clip(t, 0., 1.) * (b - a))
            out.append(ends)
        return out

    def wall(a, b, name, test=False):
        if np.linalg.norm(b[:2] - a[:2]) < .008:
            return
        band = int(max(0., min(a[2], b[2])) // 8)
        c.group = f'Safety/Crown/{name}/Band{band:02d}'
        v, f = _prism(a, b, BARRIER_THICKNESS)
        c.add(v, f, 'collision')
        barriers.append({'name': name, 'group': c.group, 'a': a.tolist(), 'b': b.tolist(),
                         'baseOffset': -.35, 'height': BARRIER_HEIGHT,
                         'thickness': BARRIER_THICKNESS,
                         'footprint': v[:4, :2].tolist()})
        if test:
            d = b - a
            normal = np.array([-d[1], d[0], 0.])
            normal /= np.linalg.norm(normal)
            mid = (a + b) / 2
            for h in (1., 7.5):
                p = mid + UP * h
                wall_tests.append({'id': name, 'group': c.group,
                                   'start': (p - normal * .55).tolist(),
                                   'end': (p + normal * .55).tolist()})

    def visible_rail(a, b, name, posts=True):
        band = int(max(0., min(a[2], b[2])) // 8)
        g.group = f'Crown/Railings/{name}/Band{band:02d}'
        for h in (.56, 1.20):
            g.beam(a + UP * h, b + UP * h, .085, M['dark'])
        g.beam(a - UP * .22, b - UP * .22, .17, M['dark'], .24)
        if posts:
            g.beam(a, a + UP * 1.27, .12, M['wood'])

    def lamp(point, side, path_name, index):
        """Lantern is over the rail, not inside the 2.8m clear walking lane."""
        p = np.asarray(point)
        band = int(max(0., p[2]) // 8)
        g.group = f'Crown/Lamps/{path_name}/Band{band:02d}'
        g.beam(p, p + UP * 3.22, .095, M['dark'])
        g.box(p + UP * 2.55, (.28, .28, .42), M['window'])
        for x in (-.165, .165):
            for y in (-.165, .165):
                g.beam(p + [x, y, 2.26], p + [x, y, 2.84], .035, M['iron'])
        for z, size in ((2.24, .40), (2.88, .44)):
            g.box(p + UP * z, (size, size, .065), M['dark'])
        light = {'position': (p + UP * 2.54 - side * .12).tolist(),
                 'range': 5.5, 'strength': 1.25,
                 'id': f'{path_name}_Lamp_{index:03d}'}
        lights.append(light)
        lamp_tests.append({'id': light['id'], 'base': p.tolist(),
                           'position': light['position'], 'wireHeight': 3.14,
                           'clearLane': True})
        return p + UP * 3.14

    route_records = []
    for path in paths:
        p, width, name = path['points'], path['width'], path['id']
        distances = _lengths(p)
        offsets = _offsets(p, width / 2)
        # Close each z-band independently for robust static MeshCollider import.
        bands = np.floor(np.maximum(0., (p[:-1, 2] + p[1:, 2]) / 2) / 8).astype(int)
        start = 0
        for end in range(1, len(p)):
            if end < len(p) - 1 and bands[end] == bands[start]:
                continue
            sub = p[start:end + 1]
            v, f = _strip_mesh(sub, width, offsets=offsets[start:end + 1])
            g.group = f'Crown/Decks/{name}/Band{bands[start]:02d}'
            c.group = f'{"Ramps" if name == "CrownHelix" else "Floors"}/{name}/Band{bands[start]:02d}'
            # Sub-centimetre visual finish separates coincident legacy/junction slabs.
            # Physics stays exactly at the authoritative route elevation.
            finish={'CrownGroundApproach':.008,'CrownArrivalBridge':.010,'CrownLookoutBridge':.012,'CrownObservatory':.014}.get(name,0.)
            g.add(v+UP*finish, f, M['wood'], v[:, :2])
            c.add(v, f, 'collision')
            start = end
        for i, point in enumerate(p):
            floor_tests.append({'id': name, 'position': point.tolist()})
            if i % 10 == 0 and 0 < i < len(p) - 1:
                for side in (-1, 1):
                    floor_tests.append({'id': name + '_Shoulder',
                                        'position': (point + offsets[i] * side *
                                                     (1. - .32 / (width / 2))).tolist()})
        for side in (-1, 1):
            edge = p + offsets * side
            for i, (a, b) in enumerate(zip(edge, edge[1:])):
                for aa, bb in clipped_edges(path, a, b):
                    wall(aa, bb, name, i % 4 == 0)
            # Visible rails use ~1.4m chord lengths. Collision retains all fine
            # segments. Always include route corners to preserve their shape.
            last = 0
            for i in range(1, len(p)):
                if distances[i] - distances[last] < 1.40 and i < len(p) - 1:
                    continue
                for aa, bb in clipped_edges(path, edge[last], edge[i]):
                    visible_rail(aa, bb, name)
                last = i
        # Regular lamp fixtures and a physically traced, sagging insulated wire.
        # The wire follows the outside edge so even the sag is outside headroom.
        ids = [0]
        next_lamp = 7.0
        for i, distance in enumerate(distances):
            if distance >= next_lamp:
                ids.append(i)
                next_lamp += 7.0
        if ids[-1] != len(p) - 1:
            ids.append(len(p) - 1)
        outside = -offsets
        wire = []
        for k, idx in enumerate(ids):
            n = outside[idx] / np.linalg.norm(outside[idx])
            loc = p[idx] + outside[idx] + n * .10
            # Avoid new poles in the old deck interior and landing openings.
            if name in legacy and legacy[name][1].buffer(.1).contains(Point(loc[:2])):
                continue
            if name != 'CrownHelix' and landing_masks[float(p[0, 2])].buffer(.10).contains(Point(loc[:2])):
                continue
            wire.append((idx, lamp(loc, n, name, k)))
        for (i0, a), (i1, b) in zip(wire, wire[1:]):
            count = max(3, int(math.ceil((distances[i1] - distances[i0]) / .8)) + 1)
            sampled = np.linspace(i0, i1, count).astype(int)
            pp = []
            for k, j in enumerate(sampled):
                t = k / (len(sampled) - 1)
                n = outside[j] / np.linalg.norm(outside[j])
                point = p[j] + outside[j] + n * .10 + UP * (3.14 - .26 * 4 * t * (1 - t))
                pp.append(point)
            pp[0], pp[-1] = a, b
            g.group = f'Crown/Wiring/{name}/Band{int(p[i0, 2] // 8):02d}'
            g.tube(pp, [.020] * len(pp), M['iron'], 5)
            wire_runs.append({'route': name, 'start': a.tolist(), 'end': b.tolist(),
                              'points': [q.tolist() for q in pp], 'diameter': .040})
        walk_points = p[distances <= distances[-1] - .60] if name == 'CrownObservatory' else p
        route_records.append({'name': name, 'type': path['type'], 'width': width,
                              'points': walk_points.tolist(), 'length': float(_lengths(walk_points)[-1]),
                              'sampleSpacingMax': float(np.linalg.norm(np.diff(walk_points, axis=0), axis=1).max()),
                              'reversible': True})

    # Horizontal stair treads on each uninterrupted rising section. 150mm is
    # a target: a section's integer count is rounded up to avoid a tall last step.
    rise_runs = [(0., 32.54), (32.54, 33.54), (34.46, 35.46),
                 (35.46, 50.54), (50.54, 51.54), (52.46, 53.46),
                 (53.46, 112.)]
    for a_t, b_t in rise_runs:
        z0, z1 = _helix_height(a_t), _helix_height(b_t)
        count = max(1, int(math.ceil((z1 - z0) / .15)))
        for i in range(count):
            t0 = a_t + (b_t - a_t) * i / count
            t1 = a_t + (b_t - a_t) * (i + 1) / count
            a, b = _helix_point(t0), _helix_point(t1)
            delta = b - a
            going = float(np.linalg.norm(delta[:2]))
            direction = np.r_[delta[:2] / going, 0.]
            left = np.array([-direction[1], direction[0], 0.])
            center = (a + b) / 2
            center[2] = b[2] - .068
            g.group = f'Crown/Treads/Band{int(a[2] // 8):02d}'
            g.box(center, (WIDTH, going + .012, .15), M['wood'], [left, direction, UP])
            tread_sizes.append([float(b[2] - a[2]), going])
    for z, low, high in ((34., 33.54, 34.46), (52., 51.54, 52.46)):
        for t in np.linspace(low, high, 13):
            p = _helix_point(t)
            a = math.radians(100. + 5. * t)
            radial = np.array([math.cos(a), math.sin(a), 0.])
            g.group = f'Crown/Landings/Z{int(z)}'
            g.beam(p - radial * WIDTH / 2 + UP * .006,
                   p + radial * WIDTH / 2 + UP * .006, .014, M['dark'])

    # Safe observatory end and the two shoulders beside the incoming staircase.
    p = crown[-1]
    radial = p.copy(); radial[2] = 0.; radial /= np.linalg.norm(radial)
    for a, b in [(p - radial * 3., p + radial * 3.)]:
        wall(a, b, 'CrownObservatoryEnd', True)
        visible_rail(a, b, 'CrownObservatoryEnd')
    p = crown[0]
    radial = p.copy(); radial[2] = 0.; radial /= np.linalg.norm(radial)
    for lo, hi in ((-3., -1.56), (1.56, 3.)):
        a, b = p + radial * lo, p + radial * hi
        wall(a, b, 'CrownObservatoryEntryShoulders', True)
        visible_rail(a, b, 'CrownObservatoryEntryShoulders')

    # Physical-looking radial timber brackets and lower ties. Their upper end
    # is below the slab, so no bracket crosses a walking lane or light wire.
    for z in np.arange(4., 112., 5.5):
        p = _helix_point(float(z))
        n = p.copy(); n[2] = 0.; n /= np.linalg.norm(n)
        root_r = float(np.interp(p[2] - 6., [0., 40., 60., 85., 108., 120.],
                                 [12., 8., 6.4, 3.8, 1.7, .15]))
        anchor = n * (root_r + .1) + UP * max(-.5, p[2] - 6.)
        g.group = f'Crown/Structure/Band{int(z // 8):02d}'
        g.beam(anchor, p - UP * .48, .28, M['dark'], .38)
        g.beam(n * (root_r + .2) + UP * (p[2] - 2.2), p - UP * .48, .12, M['iron'])
        g.beam(p - UP * .46 - n * 1.63, p - UP * .46 + n * 1.63, .24, M['dark'], .32)
    for a in np.linspace(math.radians(307.), math.radians(600.), 18):
        n = np.array([math.cos(a), math.sin(a), 0.])
        g.group = 'Crown/Structure/Observatory'
        g.beam(n * 3.1 + UP * 104., n * 22.8 + UP * 111.48, .30, M['dark'], .43)
        g.beam(n * 8. + UP * 109., n * 22.8 + UP * 111.48, .15, M['iron'])
    # Timber hoops make the top brackets read as a supported observation ring.
    for radius in (17.2, 22.8):
        pp = [np.array([radius * math.cos(a), radius * math.sin(a), 111.5])
              for a in np.linspace(math.radians(300.), math.radians(605.), 100)]
        g.tube(pp, [.15] * len(pp), M['dark'], 6)

    visual_triangles = sum(len(b['f']) for b in g.batches.values()) - before_v
    collision_triangles = sum(len(b['f']) for b in c.batches.values()) - before_c
    stairs = np.asarray(tread_sizes)
    crown_walk = np.asarray(next(x['points'] for x in route_records if x['name'] == 'CrownObservatory'))
    full_ascent = np.vstack([ground, helix[1:], crown_walk[1:]])
    route = {
        'id': 'ContinuousGroundToCrown', 'sourceCoordinates': 'XYZ_Z_UP',
        'from': 'G0', 'to': 'CrownObservatory', 'groundZ': 0., 'crownZ': CROWN_Z,
        'nominalStairWidth': WIDTH, 'clearStairWidth': WIDTH - BARRIER_THICKNESS,
        'barrierHeight': BARRIER_HEIGHT,
        'barrierThickness': BARRIER_THICKNESS,
        'mainAscentSamples': full_ascent.tolist(),
        'mainAscentLength': float(_lengths(full_ascent)[-1]),
        'sampleSpacingMax': float(np.linalg.norm(np.diff(full_ascent, axis=0), axis=1).max()),
        'landings': [{'level': 'L1', 'position': [0., -40., 34.], 'flatRun': 3.21},
                     {'level': 'L4', 'position': [40., 0., 52.], 'flatRun': 3.21},
                     {'level': 'Crown', 'position': crown[0].tolist(), 'z': 112.}],
        'connections': [
            {'from': 'G0', 'to': 'CrownGroundApproach', 'position': ground[0].tolist()},
            {'from': 'CrownGroundApproach', 'to': 'CrownHelix', 'position': base.tolist()},
            {'from': 'CrownHelix', 'to': 'L1', 'via': 'CrownArrivalBridge', 'position': [0., -40., 34.]},
            {'from': 'CrownHelix', 'to': 'L4', 'via': 'CrownLookoutBridge', 'position': [40., 0., 52.]},
            {'from': 'CrownHelix', 'to': 'CrownObservatory', 'position': crown[0].tolist()}],
        'legacyAttachmentOpenings': crown_attachment_openings(),
        'observatory': {'innerRadius': 17., 'outerRadius': 23., 'z': 112.,
                        'startAngleDegrees': 300., 'endAngleDegrees': 605.,
                        'approachNotchDegrees': [245., 300.]},
        'stats': {'visualTriangles': visual_triangles, 'collisionTriangles': collision_triangles,
                  'totalAddedTriangles': visual_triangles + collision_triangles,
                  'treadCount': len(stairs), 'minimumRiser': float(stairs[:, 0].min()),
                  'maximumRiser': float(stairs[:, 0].max()),
                  'minimumGoing': float(stairs[:, 1].min()), 'maximumGoing': float(stairs[:, 1].max()),
                  'lampCount': len(lights), 'wireRuns': len(wire_runs),
                  'barrierPrisms': len(barriers),
                  'maximumRampSlopeDegrees': float(np.degrees(np.arctan(
                      np.max(np.abs(np.diff(helix[:, 2])) /
                             np.linalg.norm(np.diff(helix[:, :2], axis=0), axis=1)))))},
    }
    cameras = [
        {'id': 'CrownCompleteAscent', 'position': [137., -154., 110.],
         'target': [0., 0., 59.], 'fov': 48, 'intent': 'Entire ground-to-crown route'},
        {'id': 'CrownArrivalConnection', 'position': [26., -61., 49.],
         'target': [0., -37., 35.], 'fov': 52, 'intent': 'Open arrival landing and lit treads'},
        {'id': 'CrownLookoutConnection', 'position': [68., 76., 76.],
         'target': [1., 22., 53.], 'fov': 55, 'intent': 'Northern skybridge and lookout connection'},
        {'id': 'CrownObservatory', 'position': [49., -56., 137.],
         'target': [0., 0., 108.], 'fov': 50, 'intent': 'Crown observatory and clear approach notch'},
    ]
    g.group, c.group = old_g, old_c
    return {'lights': lights, 'floorTests': floor_tests, 'wallTests': wall_tests,
            'routes': route_records, 'route': route, 'barriers': barriers,
            'lampTests': lamp_tests, 'wireRuns': wire_runs,
            'cameras': cameras, 'stats': route['stats']}
