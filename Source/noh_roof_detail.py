"""Additive, deterministic roof craft for the existing open Noh-inspired stage.

Source metres, X east / Y north / Z up; call before altitude conversion and
Geometry.compact(). Existing stage batches, materials and metadata are never
edited. The four exact new batches are exposed by DETAIL_ROSTER. No random
number generator is read, instantiated or consumed; no textures are created.
"""
from __future__ import annotations

import math
import numpy as np

from noh_stage import stage_layout
from timber_craft import timber_box_mesh

DETAIL_PREFIX = 'Stage/Noh/RoofDetail/'
DETAIL_ROSTER = (
    (DETAIL_PREFIX + 'Courses', 'Kawara'),
    (DETAIL_PREFIX + 'Caps', 'Kawara'),
    (DETAIL_PREFIX + 'Joinery', 'StageCypress'),
    (DETAIL_PREFIX + 'Joinery', 'DarkTimber'),
)
TILE_PITCH = .38
SHELL_THICKNESS = .008
# Nine samples of an actual curved raised-shoulder/shallow-pan section.
# cos^4 rounds the crown while broadening the concave bed; these are not
# linear subdivisions of the old folded five-station silhouette.
TILE_PROFILE = tuple((s, .045*math.cos(math.pi*s)**4)
                     for s in (0., .07, .16, .30, .50, .70, .84, .93, 1.))


def _clip(poly, axis, bound, keep_greater):
    """Clip a small convex polygon without adding an external dependency."""
    if not poly:
        return []
    out = []
    a = np.asarray(poly[-1], float)
    da = (a[axis] - bound) * (1 if keep_greater else -1)
    for b in poly:
        b = np.asarray(b, float)
        db = (b[axis] - bound) * (1 if keep_greater else -1)
        if (da >= -1e-12) != (db >= -1e-12):
            out.append(a + (b-a) * da/(da-db))
        if db >= -1e-12:
            out.append(b)
        a, da = b, db
    clean = []
    for p in out:
        if not clean or np.linalg.norm(p-clean[-1]) > 1e-10:
            clean.append(p)
    if len(clean) > 1 and np.linalg.norm(clean[-1]-clean[0]) < 1e-10:
        clean.pop()
    return clean if len(clean) >= 3 else []


def _profile_tile(g, P, anchor, U, D, N, polygon, u0, u1, d0, d1, material):
    """Closed 8 mm shell, never a solid extrusion into its curved mouth.

    The upper/lower profile strips meet at shared positions. The front cap
    covers only the ceramic thickness; it does not fill the space under the
    raised shoulders. Corner tiles are clipped to the real hip plane.
    """
    if len(polygon) < 3:
        return 0
    anchor, U, D, N = map(lambda x: np.asarray(x, float), (anchor, U, D, N))
    stations = np.array([u0 + (u1-u0)*s for s, _ in TILE_PROFILE])
    heights = np.array([h for _, h in TILE_PROFILE])
    vertices, faces, uv = [], [], []
    vertex_map = {}

    def position(p, lower=False):
        u, d = p
        # The exposed lower edge sits 16 mm above the concealed upper end.
        h = .043 + .016*(d-d0)/max(d1-d0, 1e-9) + np.interp(u, stations, heights)
        if lower:
            h -= SHELL_THICKNESS
        return P(*(anchor + U*u + D*d + N*h))

    def surface(poly, lower=False):
        indices = []
        for p in poly:
            key = (round(float(p[0]), 10), round(float(p[1]), 10), bool(lower))
            if key not in vertex_map:
                vertex_map[key] = len(vertices)
                vertices.append(position(p, lower))
                # Meter-scale coordinates keep existing clay normal maps sane.
                uv.append([float(p[0]), float(p[1])])
            indices.append(vertex_map[key])
        for k in range(1, len(indices)-1):
            f = [indices[0], indices[k], indices[k+1]]
            q = np.asarray([vertices[i] for i in f])
            if np.linalg.norm(np.cross(q[1]-q[0], q[2]-q[0])) > 1e-12:
                faces.append(f[::-1] if lower else f)

    for a, b in zip(stations, stations[1:]):
        strip = _clip(_clip(polygon, 0, a, True), 0, b, False)
        if strip:
            surface(strip)
            surface(strip, True)
    g.add(vertices, faces, material, uv)
    triangles = len(faces)
    # Subdivide the boundary where a curved-profile station meets the lip.
    # The side UV is distance x thickness, not a collapsed XY projection.
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        a, b = np.asarray(a), np.asarray(b)
        splits = [0., 1.]
        if abs(b[0]-a[0]) > 1e-10:
            splits += [float((s-a[0])/(b[0]-a[0])) for s in stations
                       if 1e-9 < (s-a[0])/(b[0]-a[0]) < 1-1e-9]
        splits = sorted(set(splits))
        for ta, tb in zip(splits, splits[1:]):
            p, q = a+(b-a)*ta, a+(b-a)*tb
            length = float(np.linalg.norm(position(q)-position(p)))
            if length < 1e-9:
                continue
            g.quad([position(p), position(p, True), position(q, True), position(q)],
                   material, [(0, SHELL_THICKNESS), (0, 0), (length, 0),
                              (length, SHELL_THICKNESS)])
            triangles += 2
    return triangles


def _roof_courses(g, P, side, hip, material):
    rise = 1.18
    run = 1.45 if hip else 2.85
    length = math.hypot(run, rise)
    c, s = run/length, rise/length
    if hip:
        anchor = [side*1.45, 0, 4.17]
        U, D, N = [0, -side, 0], [side*c, 0, -s], [side*s, 0, c]
        width = lambda d: 2.85*d/length
        rows = 6
    else:
        anchor = [0, 0, 4.17]
        U, D, N = [side, 0, 0], [0, side*c, -s], [0, side*s, c]
        width = lambda d: 1.45+1.45*d/length
        rows = 9
    tiles = 0
    course_rows = []
    for row in range(rows):
        d0 = max(.015, row*length/rows-.045)
        d1 = min(length, (row+1)*length/rows)
        # Trim 18 mm at each hip boundary; the original core and new cap bridge it.
        w0, w1 = max(0., width(d0)-.018), max(0., width(d1)-.018)
        row_polygon = [np.array(p) for p in [(-w0, d0), (w0, d0), (w1, d1), (-w1, d1)]]
        offset = 0.  # Pan/roll channels align down-slope, unlike brick bond.
        count = 0
        for col in range(math.floor((-w1-offset)/TILE_PITCH),
                         math.ceil((w1-offset)/TILE_PITCH)):
            u0, u1 = col*TILE_PITCH+offset+.0015, (col+1)*TILE_PITCH+offset-.0015
            polygon = _clip(_clip(row_polygon, 0, u0, True), 0, u1, False)
            if not polygon:
                continue
            area = abs(sum(a[0]*b[1]-b[0]*a[1]
                           for a, b in zip(polygon, polygon[1:]+polygon[:1])))*.5
            if area < .00010:
                continue
            _profile_tile(g, P, anchor, U, D, N, polygon, u0, u1, d0, d1, material)
            tiles += 1
            count += 1
        course_rows.append(count)
    return {'side': side, 'hip': hip, 'rows': rows, 'tiles': tiles,
            'tileCountsByCourse': course_rows, 'coursePitchMetres': length/rows,
            'overlapMetres': .045}


def _cap_shell(g, P, a, b, material, radius=.086, thickness=.010):
    """A segment of rounded ridge/hip cap with a real thin annular end rim.

    The original closed .075 m tube remains underneath as the protected core.
    No hollow interior is claimed for that pre-existing structural core.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    tangent = b-a
    length = np.linalg.norm(tangent)
    tangent /= length
    across = np.cross([0, 0, 1], tangent)
    across /= np.linalg.norm(across)
    up = np.cross(tangent, across)
    n = 6
    v, f, uv = [], [], []
    for r in [radius, radius-thickness]:
        for p in [a, b]:
            for j in range(n+1):
                theta = math.pi*j/n
                v.append(P(*(p + across*math.cos(theta)*r + up*math.sin(theta)*r)))
                uv.append([theta*r, 0. if np.array_equal(p, a) else length])
    k = n+1
    for j in range(n):
        # cross(across curve tangent, along) points outside the upper shell.
        f += [(j, j+1, k+j+1), (j, k+j+1, k+j)]
        f += [(2*k+j, 3*k+j+1, 2*k+j+1), (2*k+j, 3*k+j, 3*k+j+1)]
    g.add(v, f, material, uv)
    for end in [0, 1]:
        for j in range(n):
            indices = [end*k+j, (2+end)*k+j, (2+end)*k+j+1, end*k+j+1]
            q = [v[i] for i in indices]
            u = [(j*radius*math.pi/n, thickness), (j*radius*math.pi/n, 0),
                 ((j+1)*radius*math.pi/n, 0), ((j+1)*radius*math.pi/n, thickness)]
            if end:
                q, u = q[::-1], u[::-1]
            g.quad(q, material, u)
    for j in [0, n]:
        indices = [j, k+j, 3*k+j, 2*k+j]
        q = [v[i] for i in indices]
        u = [(0, thickness), (length, thickness), (length, 0), (0, 0)]
        if j == n:
            q, u = q[::-1], u[::-1]
        g.quad(q, material, u)


def add_noh_roof_detail(g, M, rng=None):
    """Append exactly four batches; return separate visual-only cost metadata."""
    del rng
    if any(key[0].startswith(DETAIL_PREFIX) for key in g.batches):
        raise ValueError('Noh roof details already exist; additive pass must run once')
    for _, material in DETAIL_ROSTER:
        if material not in g.materials:
            raise ValueError('Existing stage/material authoring must precede roof details: '+material)
    spec = stage_layout()
    origin, right, front = map(np.asarray, (spec['center'], spec['right'], spec['front']))
    axes = [right, front, [0, 0, 1]]
    P = lambda x, y, z: origin + right*x + front*y + [0, 0, z]
    old_group = g.group
    courses = []
    try:
        g.group = DETAIL_PREFIX+'Courses'
        for hip in [False, True]:
            for side in [-1, 1]:
                courses.append(_roof_courses(g, P, side, hip, M['tile']))
        g.group = DETAIL_PREFIX+'Caps'
        # Keep the familiar low ridge profile. Segmented seams add scale.
        ridge_caps = 9
        for j in range(ridge_caps):
            x0 = -1.45+j*2.90/ridge_caps
            x1 = -1.45+(j+1)*2.90/ridge_caps
            _cap_shell(g, P, [x0+.003, 0, 4.190], [x1-.003, 0, 4.190],
                       M['tile'], radius=.081, thickness=.009)
        hip_caps = 0
        for xside in [-1, 1]:
            for yside in [-1, 1]:
                eave = np.array([xside*2.9, yside*2.85, 3.010])
                ridge = np.array([xside*1.45, 0., 4.190])
                for j in range(8):
                    # First rim is inset 25 mm along the original hip axis.
                    t0 = .008 if j == 0 else j/8+.001
                    t1 = (j+1)/8-.001
                    _cap_shell(g, P, eave+(ridge-eave)*t0,
                               eave+(ridge-eave)*t1, M['tile'], radius=.084)
                    hip_caps += 1
        g.group = DETAIL_PREFIX+'Joinery'
        cypress, dark = 'StageCypress', M['dark']
        # Pegged upper beam joints: shadow rebates, chamfered plugs, wooden pins.
        # Set 400 mm inboard of the pillar center to expose the joints rather
        # than burying them inside the protected original bracket/knee braces.
        # Every detail is above 2.757 m, clear of the fixed performance volume.
        for x in [-1.84, 1.84]:
            for y in [-1.84, 1.84]:
                sx, sy = math.copysign(1, x), math.copysign(1, y)
                for face in [0, 1]:
                    if face == 0:
                        p, size = P(x-sx*.40, y+sy*.112, 2.825), [.184, .016, .080]
                        tongue, ts = P(x-sx*.40, y+sy*.125, 2.825), [.132, .022, .056]
                        pins = [(P(x-sx*.40+dx, y+sy*.134, 2.825),
                                 P(x-sx*.40+dx, y+sy*.157, 2.825)) for dx in [-.040, .040]]
                    else:
                        p, size = P(x+sx*.112, y-sy*.40, 2.825), [.016, .184, .080]
                        tongue, ts = P(x+sx*.125, y-sy*.40, 2.825), [.022, .132, .056]
                        pins = [(P(x+sx*.134, y-sy*.40+dy, 2.825),
                                 P(x+sx*.157, y-sy*.40+dy, 2.825)) for dy in [-.040, .040]]
                    g.box(p, size, dark, axes)
                    v, f, uv = timber_box_mesh(tongue, ts, axes, bevel=.003)
                    g.add(v, f, cypress, uv)
                    for a, b in pins:
                        g.tube([a, b], [.009, .009], dark, 6)
        # Hip jack rafters complete the two formerly sparse end soffits.
        for side in [-1, 1]:
            for y in [-1.90, -1.14, -.38, .38, 1.14, 1.90]:
                inner_t = abs(y)/2.85
                x0 = side*(1.45+1.45*inner_t)
                z0 = 4.17-1.18*inner_t-.155
                g.beam(P(x0, y, z0), P(side*2.81, y, 2.94-.155),
                       .055, cypress, .075)
    finally:
        g.group = old_group
    keys = tuple(key for key in g.batches if key[0].startswith(DETAIL_PREFIX))
    if set(keys) != set(DETAIL_ROSTER):
        raise AssertionError('Unexpected additive Noh roof batch roster')
    vertices = np.concatenate([np.asarray(g.batches[key]['v']) for key in keys])
    local = (vertices-origin) @ np.array([right, front, [0, 0, 1]]).T
    return {
        'schema': 'NohRoofDetail/1', 'visualOnly': True,
        'originalStageBatchesModified': 0, 'collisionAuthored': False,
        'newMaterials': 0, 'newTextures': 0, 'randomDraws': 0,
        'addedBatches': len(keys),
        'addedTriangles': sum(len(g.batches[key]['f']) for key in keys),
        'localBounds': [local.min(0).tolist(), local.max(0).tolist()],
        'tileShellThicknessMetres': SHELL_THICKNESS,
        'tilePitchMetres': TILE_PITCH, 'tileProfileStations': len(TILE_PROFILE),
        'tileProfileCurve': '0.045*cos(pi*s)^4, sampled at nine nonuniform cross-section stations',
        'courses': courses,
        'ridgeCapSegments': ridge_caps, 'hipCapSegments': hip_caps,
        'upperBeamEndJoints': 8, 'woodenPins': 16, 'hipJackRafters': 12,
        'scope': 'Additive modeled roofing and joinery; no runtime or historic-fidelity certification.',
    }
