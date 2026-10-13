"""Continuous high-canopy ground-to-crown circulation for TreeTopYokocho (source XYZ, Z up).

The walking collider is a closed swept ramp, not 1,400 separate step colliders.
Visual treads, railings, lamps, wiring and brackets are independently batched.
See Docs/HighCrownStairs.md for integration and validation contracts.
"""
from __future__ import annotations

import math
import numpy as np
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union

UP = np.array([0., 0., 1.])
WIDTH = 2.8
GROUND_Z = 0.0
ARRIVAL_Z = 134.0
LOOKOUT_Z = 152.0
CROWN_Z = 212.0
LANDING_HALF_RUN = .46
LANDING_TRANSITION = 1.46
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
    for h in (ARRIVAL_Z, LOOKOUT_Z):
        d = t - h
        if abs(d) <= LANDING_HALF_RUN:
            return h
        if abs(d) < LANDING_TRANSITION:
            return h + math.copysign((abs(d) - LANDING_HALF_RUN) * LANDING_TRANSITION, d)
    return z


def _helix_angle(t):
    """Two extra lower turns; identical upper-route XY at the raised joins.

    The lower route turns 100 -> 990 degrees over Z0 -> Z134. Its arrival is
    exactly south at (0,-40). The upper route turns 990 -> 1380 degrees,
    reaching east at Z152 and the observatory's 300-degree entry at Z212.
    """
    return math.radians(100. + 890. * t / ARRIVAL_Z if t <= ARRIVAL_Z
                        else 990. + 5. * (t - ARRIVAL_Z))


def _helix_point(t):
    z = _helix_height(t)
    u = np.clip((z - LOOKOUT_Z) / (CROWN_Z - LOOKOUT_Z), 0., 1.)
    radius = 40. - 20. * (3 * u * u - 2 * u * u * u)
    a = _helix_angle(t)
    return np.array([radius * math.cos(a), radius * math.sin(a), z])


def _trunk_anchor(height, radial):
    """Embed a support root in the remapped, slightly drifting tree trunk.

    Original trunk Z<=14 stays fixed; Z14..33 uses the altitude module's
    smoothstep +100m mapping; all higher trunk geometry is translated +100m.
    The 60%-radius attachment tolerates bark ridges and interpolated rings.
    """
    low, high = -1., 119.
    for _ in range(40):
        original = (low + high) / 2
        u = float(np.clip((original - 14.) / 19., 0., 1.))
        remapped = original + 100. * u * u * (3. - 2. * u)
        if remapped < height:
            low = original
        else:
            high = original
    z = (low + high) / 2
    radius = float(np.interp(z, [-1., 0., 20., 40., 60., 85., 108., 119.],
                             [13.8, 13., 9.6, 8., 6.4, 3.8, 1.7, .15]))
    return np.array([.9 * math.sin(z * .075), 1.5 * math.sin(z * .047), height]) + radial * radius * .60


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
        {'id': 'Crown_L1_Arrival', 'level': 'L1', 'z': ARRIVAL_Z, 'width': 3.0,
         'centerline': [[0., -40., ARRIVAL_Z], [0., -32., ARRIVAL_Z]],
         'bounds': [-1.65, -40.4, 1.65, -31.6]},
        {'id': 'Crown_L4_Lookout', 'level': 'L4', 'z': LOOKOUT_Z, 'width': 3.0,
         'centerline': [[44. * math.cos(math.radians(141.)),
                         44. * math.sin(math.radians(141.)), LOOKOUT_Z],
                        [-28., 24., LOOKOUT_Z]],
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

    critical = [h + d for h in (ARRIVAL_Z, LOOKOUT_Z)
                for d in (-LANDING_TRANSITION, -LANDING_HALF_RUN, 0.,
                          LANDING_HALF_RUN, LANDING_TRANSITION)]
    # Keep lower samples just below the 0.44m budget instead of repeatedly
    # splitting 0.1-height stations in half after the additional winding.
    tt = sorted(set(np.linspace(GROUND_Z, ARRIVAL_Z, 1601).tolist() +
                    np.linspace(ARRIVAL_Z, CROWN_Z, 781).tolist() + critical))
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
    arrival = _resample([[0., -40., ARRIVAL_Z], [0., -32., ARRIVAL_Z]])
    north_arc = [np.array([44. * math.cos(a), 44. * math.sin(a), LOOKOUT_Z])
                 for a in np.linspace(0., math.radians(132.), 232)]
    corner = np.array([44. * math.cos(math.radians(141.)),
                       44. * math.sin(math.radians(141.)), LOOKOUT_Z])
    end = np.array([-28., 24., LOOKOUT_Z])
    direction = end - corner; direction /= np.linalg.norm(direction)
    curve_end = corner + direction * 4.4
    curve = [(1 - t) ** 2 * north_arc[-1] +
             2 * (1 - t) * t * corner + t * t * curve_end
             for t in np.linspace(0., 1., 41)[1:]]
    lookout = _resample([[40., 0., LOOKOUT_Z], *north_arc, *curve, end])
    # The 55-degree notch is essential: a full annulus would put a slab across
    # the last ~8 vertical metres of the stair and its tall safety walls.
    crown = _resample([[20. * math.cos(a), 20. * math.sin(a), CROWN_Z]
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
    landing_masks = {}
    for z in (GROUND_Z, ARRIVAL_Z, LOOKOUT_Z, CROWN_Z):
        near = helix[np.abs(helix[:, 2] - z) < (.24 if z in (GROUND_Z, CROWN_Z) else .00001)]
        landing_masks[z] = _footprint(near, WIDTH) if len(near) > 1 else Point(_helix_point(z)[:2]).buffer(1.4)
    legacy = {'CrownGroundApproach': (0., box(-26., -37., -6., -21.)),
              'CrownArrivalBridge': (ARRIVAL_Z, box(-10., -34., 10., -18.)),
              'CrownLookoutBridge': (LOOKOUT_Z, box(-29.5, 18., -20.5, 26.))}

    def masks_for(path, a, b):
        h = (a[2] + b[2]) / 2
        result = []
        if path['id'] == 'CrownHelix':
            for z, idx in ((GROUND_Z, 0), (ARRIVAL_Z, 2), (LOOKOUT_Z, 3), (CROWN_Z, 4)):
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
            # Distinct 8–14 mm visual finishes separates coincident legacy/junction slabs.
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
    rise_runs = [(GROUND_Z, ARRIVAL_Z - LANDING_TRANSITION),
                 (ARRIVAL_Z - LANDING_TRANSITION, ARRIVAL_Z - LANDING_HALF_RUN),
                 (ARRIVAL_Z + LANDING_HALF_RUN, ARRIVAL_Z + LANDING_TRANSITION),
                 (ARRIVAL_Z + LANDING_TRANSITION, LOOKOUT_Z - LANDING_TRANSITION),
                 (LOOKOUT_Z - LANDING_TRANSITION, LOOKOUT_Z - LANDING_HALF_RUN),
                 (LOOKOUT_Z + LANDING_HALF_RUN, LOOKOUT_Z + LANDING_TRANSITION),
                 (LOOKOUT_Z + LANDING_TRANSITION, CROWN_Z)]
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
    for z in (ARRIVAL_Z, LOOKOUT_Z):
        low, high = z - LANDING_HALF_RUN, z + LANDING_HALF_RUN
        for t in np.linspace(low, high, 13):
            p = _helix_point(t)
            a = _helix_angle(t)
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
    for z in np.arange(4., CROWN_Z, 5.5):
        p = _helix_point(float(z))
        n = p.copy(); n[2] = 0.; n /= np.linalg.norm(n)
        anchor = _trunk_anchor(max(-.5, p[2] - 6.), n)
        g.group = f'Crown/Structure/Band{int(z // 8):02d}'
        g.beam(anchor, p - UP * .48, .28, M['dark'], .38)
        g.beam(_trunk_anchor(p[2] - 2.2, n), p - UP * .48, .12, M['iron'])
        g.beam(p - UP * .46 - n * 1.63, p - UP * .46 + n * 1.63, .24, M['dark'], .32)
    for a in np.linspace(math.radians(307.), math.radians(600.), 18):
        n = np.array([math.cos(a), math.sin(a), 0.])
        g.group = 'Crown/Structure/Observatory'
        g.beam(_trunk_anchor(CROWN_Z - 8., n), n * 22.8 + UP * (CROWN_Z - .52), .30, M['dark'], .43)
        g.beam(_trunk_anchor(CROWN_Z - 3., n), n * 22.8 + UP * (CROWN_Z - .52), .15, M['iron'])
    # Timber hoops make the top brackets read as a supported observation ring.
    for radius in (17.2, 22.8):
        pp = [np.array([radius * math.cos(a), radius * math.sin(a), CROWN_Z - .5])
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
        'helixTurns': (math.degrees(_helix_angle(CROWN_Z) - _helix_angle(GROUND_Z)) / 360.),
        'legacyHeightOffset': 100.,
        'mainAscentSamples': full_ascent.tolist(),
        'mainAscentLength': float(_lengths(full_ascent)[-1]),
        'sampleSpacingMax': float(np.linalg.norm(np.diff(full_ascent, axis=0), axis=1).max()),
        'landings': [{'level': 'L1', 'position': [0., -40., ARRIVAL_Z], 'flatRun': float(_lengths(helix[np.abs(helix[:, 2] - ARRIVAL_Z) < 1e-6])[-1])},
                     {'level': 'L4', 'position': [40., 0., LOOKOUT_Z], 'flatRun': float(_lengths(helix[np.abs(helix[:, 2] - LOOKOUT_Z) < 1e-6])[-1])},
                     {'level': 'Crown', 'position': crown[0].tolist(), 'z': CROWN_Z}],
        'connections': [
            {'from': 'G0', 'to': 'CrownGroundApproach', 'position': ground[0].tolist()},
            {'from': 'CrownGroundApproach', 'to': 'CrownHelix', 'position': base.tolist()},
            {'from': 'CrownHelix', 'to': 'L1', 'via': 'CrownArrivalBridge', 'position': [0., -40., ARRIVAL_Z]},
            {'from': 'CrownHelix', 'to': 'L4', 'via': 'CrownLookoutBridge', 'position': [40., 0., LOOKOUT_Z]},
            {'from': 'CrownHelix', 'to': 'CrownObservatory', 'position': crown[0].tolist()}],
        'legacyAttachmentOpenings': crown_attachment_openings(),
        'observatory': {'innerRadius': 17., 'outerRadius': 23., 'z': CROWN_Z,
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
        {'id': 'CrownCompleteAscent', 'position': [260., -280., 208.],
         'target': [0., 0., 108.], 'fov': 48, 'intent': 'Entire ground-to-crown route'},
        {'id': 'CrownArrivalConnection', 'position': [26., -61., 149.],
         'target': [0., -37., 135.], 'fov': 52, 'intent': 'Open arrival landing and lit treads'},
        {'id': 'CrownLookoutConnection', 'position': [68., 76., 176.],
         'target': [1., 22., 153.], 'fov': 55, 'intent': 'Northern skybridge and lookout connection'},
        {'id': 'CrownObservatory', 'position': [49., -56., 237.],
         'target': [0., 0., 208.], 'fov': 50, 'intent': 'Crown observatory and clear approach notch'},
    ]
    g.group, c.group = old_g, old_c
    return {'lights': lights, 'floorTests': floor_tests, 'wallTests': wall_tests,
            'routes': route_records, 'route': route, 'barriers': barriers,
            'lampTests': lamp_tests, 'wireRuns': wire_runs,
            'cameras': cameras, 'stats': route['stats']}


def validate_standalone():
    """Verify actual serialized colliders without invoking the world generator.

    The three original attachment floor rectangles are explicit fixtures: a
    bridge ending inside a legacy deck requires that deck to support the part
    of the avatar beyond its endpoint. No original obstacle/guard is simulated.
    Independent ray and clipped-solid kernels come from validate_crown.py.
    The generator is never used to decide whether a probe should pass.
    """
    import tempfile
    import time
    from pathlib import Path
    import trimesh
    from world_geometry import Geometry, poly_mesh
    from validate_crown import Rays, Solids, densified_segments, read_collision

    started=time.time()
    g,c=Geometry(),Geometry()
    M={x:g.material(x,[.5,.5,.5]) for x in ('wood','dark','window','iron')}
    c.material('collision',[1,1,1])
    g.group,c.group='KeepVisual','KeepCollider'
    rng=np.random.default_rng(444); state=repr(rng.bit_generator.state)
    r=add_crown_stairs(g,c,M,rng)
    assert (g.group,c.group)==('KeepVisual','KeepCollider')
    assert state==repr(rng.bit_generator.state)
    # These three pre-existing attachment slabs are the module's documented
    # integration boundary, including the half-avatar beyond bridge endpoints.
    for name, bounds, z in [('G0',(-26,-37,-6,-21),0),('L1',(-10,-34,10,-18),134),('L4',(-29.5,18,-20.5,26),152)]:
        c.group='Floors/LegacyFixture/'+name
        v,f=poly_mesh(box(*bounds),z)
        c.add(v,f,'collision')
    with tempfile.TemporaryDirectory(prefix='high-crown-test-') as folder:
        payload=Path(folder)/'CollisionMeshes.bytes'
        c.save_binary(payload)
        meshes=read_collision(payload)
    floors,walls,obstacles,floor_records=[],[],[],[]
    for m in meshes:
        tri=m['triangles']; name=m['group']
        if name.startswith(('Floors/','Ramps/')):
            mesh=trimesh.Trimesh(m['vertices'],m['faces'],process=True)
            assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,(name,'closed slab')
            floors.extend(tri)
            floor_records.extend({'name':f'{name} triangle {i}','triangles':x[None]} for i,x in enumerate(tri))
        elif name.startswith('Safety/Crown/'):
            assert len(tri)%12==0,name
            for i in range(0,len(tri),12):
                t=tri[i:i+12]
                assert len(np.unique(t.reshape(-1,3),axis=0))==8,(name,i)
                mesh=trimesh.Trimesh(t.reshape(-1,3),np.arange(36).reshape(-1,3),process=True)
                assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,(name,i,'closed wall')
                obstacles.append({'name':f'{name} prism {i//12}','triangles':t})
            walls.extend(tri)
        else:raise AssertionError(name)
    normals=np.cross(np.asarray(floors)[:,1]-np.asarray(floors)[:,0],np.asarray(floors)[:,2]-np.asarray(floors)[:,0])
    top=normals[normals[:,2]>1e-6]
    maximum_surface_slope=float(np.degrees(np.arctan(np.linalg.norm(top[:,:2],axis=1)/top[:,2])).max())
    assert maximum_surface_slope <=32,maximum_surface_slope
    floor_rays,wall_rays=Rays(floors),Rays(walls)
    solids,floor_solids=Solids(obstacles),Solids(floor_records)
    failures=[]
    counts={'floorProbes':0,'centerProbes':0,'radialSupportProbes':0,'sweptSegments':0,'guardRays':0,'safetyPrisms':len(obstacles),'floorTriangles':len(floors)}
    for q in r['floorTests']:
        p=np.array(q['position']);counts['floorProbes']+=1
        hit=floor_rays.hit(p+[0,0,.75],[0,0,-1],1.65)
        if hit is None or abs(hit-.75)>.04:failures.append(('emittedfloor',q,hit))
    offsets=[np.array([math.cos(a)*.25,math.sin(a)*.25,0.]) for a in np.linspace(0,math.tau,8,endpoint=False)]
    for route in r['routes']:
        p=np.asarray(route['points'])
        assert np.isfinite(p).all() and np.linalg.norm(np.diff(p,axis=0),axis=1).max()<=.440001
        for q in p:
            counts['centerProbes']+=1
            hit=floor_rays.hit(q+[0,0,.75],[0,0,-1],1.5)
            if hit is None or abs(hit-.75)>.035:failures.append(('center',route['name'],q.tolist(),hit))
            if counts['centerProbes']%2==0:
                for off in offsets:
                    counts['radialSupportProbes']+=1
                    hit=floor_rays.hit(q+off+[0,0,.75],[0,0,-1],1.5)
                    if hit is None or abs(hit-.75)>.27:failures.append(('support',route['name'],(q+off).tolist(),hit))
        for a,b in densified_segments(p):
            counts['sweptSegments']+=1
            footprint=LineString([a[:2],b[:2]]).buffer(.25,quad_segs=8)
            low,high=min(a[2],b[2]),max(a[2],b[2])
            hits=solids.intersections(footprint,low+.055,high+1.65)
            if hits:failures.append(('body',route['name'],a.tolist(),hits[:6]))
            hits=solids.intersections(footprint,low+1.65,high+2.2)+floor_solids.intersections(footprint,low+.32,high+2.2)
            if hits:failures.append(('headroom',route['name'],a.tolist(),hits[:6]))
    for q in r['wallTests']:
        a,b=np.asarray(q['start']),np.asarray(q['end']);d=b-a;l=np.linalg.norm(d);counts['guardRays']+=1
        if wall_rays.hit(a,d/l,l) is None:failures.append(('guard',q))
    routes={x['name']:np.asarray(x['points']) for x in r['routes']}
    assert np.linalg.norm(routes['CrownGroundApproach'][-1]-routes['CrownHelix'][0])<1e-7
    assert np.linalg.norm(routes['CrownHelix'][-1]-routes['CrownObservatory'][0])<1e-7
    for name in ['CrownArrivalBridge','CrownLookoutBridge']:
        assert np.linalg.norm(routes['CrownHelix']-routes[name][0],axis=1).min()<1e-7
    for name,expected in [('CrownGroundApproach',[-20,-29,0]),('CrownArrivalBridge',[0,-32,134]),('CrownLookoutBridge',[-28,24,152])]:
        assert np.allclose(routes[name][0 if name=='CrownGroundApproach' else -1],expected,rtol=0,atol=1e-8)
    asc=np.asarray(r['route']['mainAscentSamples']); assert asc[0,2]==0 and asc[-1,2]==212
    assert np.diff(asc[:,2]).min()>-1e-9 and np.linalg.norm(np.diff(asc,axis=0),axis=1).max()<=.440001
    assert r['stats']['maximumRampSlopeDegrees']<=32
    assert r['stats']['maximumRiser']<=.150000001
    assert r['stats']['minimumRiser']>=.145999999
    result={'scope':'Standalone float32 collider regression with three attachment-slab fixtures; not whole-world or Unity/VRChat runtime verification.','status':'FAIL' if failures else 'PASS','counts':counts,'stats':r['stats'],'ascentLength':r['route']['mainAscentLength'],'helixTurns':r['route']['helixTurns'],'landings':r['route']['landings'],'maximumActualFloorTriangleSlopeDegrees':maximum_surface_slope,'failureCount':len(failures),'failures':failures[:80],'elapsedSeconds':time.time()-started}
    return result


def _main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true',
                        help='Run standalone float32 collider/support/body/headroom checks')
    parser.add_argument('--report', type=Path, help='Optional destination for the JSON test report')
    args = parser.parse_args()
    if not args.self_test:
        parser.print_help()
        return 0
    result = validate_standalone()
    text = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text, end='')
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(_main())
