"""Lightweight, directional fantasy landscape for the 120 m Tree-top Yokocho.

Drop-in replacement for high_detail.landscape(g, materials, rng).
All coordinates are metres in source X=east, Y=north, Z=up.  This module
creates visual scenery only.  It never changes the shop or collision geometry.
The city is north; the sea and *water-rooted* islands are south.
"""
import math
import numpy as np

TAU = math.tau
CITY_CENTER = (0.0, 740.0)
CITY_RADIUS = 162.0
SEA_LEVEL = -4.02

# A deliberately asymmetric coast, not another circular island/lake.
def coast_y(x):
    x = np.asarray(x)
    return -410.0 + 64*np.sin(x*.0025+.8) + 36*np.sin(x*.0062-.7) + 17*np.sin(x*.012)


def terrain_height(x, y):
    """Deterministic visual ground height; accepts scalar or numpy arrays.

    The root/arrival zone remains low and flat under the original rock bed.
    This is exposed for an independent ground-collider author, but this module
    intentionally supplies no new traversability claims or distant colliders.
    """
    x, y = np.asarray(x), np.asarray(y)
    r = np.hypot(x, y)
    influence = np.clip((r-65.0)/170.0, 0, 1)
    relief = (4.8 + 3.4*np.sin(x*.007+y*.0013)
              + 2.3*np.sin(y*.012-x*.0037) + 1.2*np.cos(x*.024+y*.009))
    h = -1.65 + influence*relief
    h += np.maximum(y-1050, 0)*.025
    # A broad, soft terrace gives the fortified city a believable level site.
    city_d = np.hypot(x-CITY_CENTER[0], y-CITY_CENTER[1])
    terrace = np.clip((232.0-city_d)/48.0, 0, 1)
    terrace = terrace*terrace*(3-2*terrace)
    h = h*(1-terrace) + 12.0*terrace
    coast_distance = y-coast_y(x)
    shore = np.clip(coast_distance/38.0, 0, 1)
    shore = shore*shore*(3-2*shore)
    h = (SEA_LEVEL-.55)*(1-shore) + h*shore
    return float(h) if np.ndim(h) == 0 else h


# The approach avoids the tree's protected centre and ends at the south gate.
ROAD_CONTROL = np.array([
    [-27., -34.], [-43., -15.], [-49., 23.], [-40., 76.],
    [-16., 140.], [11., 221.], [-7., 326.], [18., 431.],
    [10., 518.], [0., 584.],
])


def road_points():
    """Sample a smooth northbound approach, including both endpoints."""
    points = []
    for i in range(len(ROAD_CONTROL)-1):
        p0, p1 = ROAD_CONTROL[max(0, i-1)], ROAD_CONTROL[i]
        p2, p3 = ROAD_CONTROL[i+1], ROAD_CONTROL[min(len(ROAD_CONTROL)-1, i+2)]
        n = max(4, int(np.linalg.norm(p2-p1)/6))
        for t in np.linspace(0, 1, n, endpoint=False):
            points.append(.5*((2*p1)+(-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t
                               + (-p0+3*p1-3*p2+p3)*t*t*t))
    points.append(ROAD_CONTROL[-1])
    return np.asarray(points)


def _road_distance(x, y, points):
    q = np.array([x, y]); a = points[:-1]; d = points[1:]-a
    t = np.clip(np.sum((q-a)*d, axis=1)/np.sum(d*d, axis=1), 0, 1)
    return float(np.min(np.linalg.norm(q-a-d*t[:, None], axis=1)))


def _ribbon(g, points, width, material, lift=.06):
    v, uv, f = [], [], []
    distance = 0.
    for i, point in enumerate(points):
        delta = points[min(i+1, len(points)-1)]-points[max(i-1, 0)]
        side = np.array([-delta[1], delta[0]])/np.linalg.norm(delta)
        if i: distance += np.linalg.norm(point-points[i-1])
        for sign in [-1, 1]:
            xy = point+side*width*.5*sign
            v.append([*xy, terrain_height(*xy)+lift]); uv.append([(sign+1)*.5, distance*.05])
        if i:
            k = i*2
            f.extend([(k-2, k, k+1), (k-2, k+1, k-1)])
    g.add(v, f, material, uv)


def _original_root_bed(g, stone):
    """Keep the previous central bedrock geometry byte-for-byte in source space."""
    g.group = 'Landscape/TreeIsland'  # Stable historical group; now land-connected.
    n = 96; v = [[0, 0, -.8]]; uv = [[0, 0]]; f = []
    for ring in range(1, 15):
        for j in range(n):
            a = j*TAU/n
            r = ring/14*(52+4*math.sin(a*5)+3*math.cos(a*9))
            h = -.6-(r/54)**4*4+.24*math.sin(a*11)*ring/14
            v.append([r*math.cos(a), r*math.sin(a), h])
            uv.append([v[-1][0]*.2, v[-1][1]*.2])
            if ring == 1: f.append((0, 1+j, 1+(j+1)%n))
            else:
                k = 1+(ring-1)*n+j; kn = 1+(ring-1)*n+(j+1)%n
                f.extend([(k-n, k, kn), (k-n, kn, kn-n)])
    g.add(v, f, stone, uv)


def _land(g, m):
    # A single continuous coastal mainland. Adjacent sectors share identical
    # edge samples. Near samples are denser; the empty far field is coarse.
    xs = np.unique(np.r_[np.linspace(-2600, -650, 28), np.linspace(-650, 650, 105),
                         np.linspace(650, 2600, 28)])
    offsets = np.r_[0., 8., 18., 30., np.linspace(45, 1120, 91),
                    np.linspace(1160, 2300, 26), np.linspace(2400, 4100, 18)]
    cuts = np.linspace(0, len(xs)-1, 9, dtype=int)
    for sector, (start, end) in enumerate(zip(cuts, cuts[1:])):
        g.group = 'Landscape/Mainland_%02d'%sector
        v, f, uv = [], [], []
        xx = xs[start:end+1]; nx = len(xx)
        for j, offset in enumerate(offsets):
            for i, x in enumerate(xx):
                y = float(coast_y(x))+offset
                v.append([x, y, terrain_height(x, y)]); uv.append([x*.055, y*.055])
                if i and j:
                    k = j*nx+i
                    f.extend([(k-nx-1, k-nx, k), (k-nx-1, k, k-1)])
        g.add(v, f, m['terrain'], uv)
    return 8


def _sea(g, m):
    # Opaque water is only south of the mainland. Four spatial batches improve
    # culling and avoid an unnecessary full-world water sheet under the forest.
    for sector in range(4):
        g.group = 'Landscape/Sea_%d'%sector
        nx, ny = 31, 25; v, uv, f = [], [], []
        for j in range(ny):
            for i in range(nx):
                x = -6300+(sector+i/(nx-1))*3150
                y = float(coast_y(x)) - (j/(ny-1))**1.30*5400
                v.append([x, y, SEA_LEVEL]); uv.append([x*.018, y*.018])
                if i and j:
                    k = j*nx+i
                    # South-going rows need the opposite winding to mainland.
                    f.extend([(k-nx-1, k, k-nx), (k-nx-1, k-1, k)])
        g.add(v, f, m['lake'], uv)


def _crown(g, centre, scale, material, sides=8, rings=4):
    # Closed opaque foliage, with actual silhouette lobes: no billboard stacks,
    # transparent shells, alpha overdraw, or added foliage texture downloads.
    # Explicit single poles avoid the legacy noisy-sphere pole splits.
    centre, scale = np.asarray(centre), np.asarray(scale)
    v = [centre+[0, 0, scale[2]]]; uv = [[.5, 1.]]; f = []
    for i in range(1, rings):
        a = math.pi*i/rings
        for j in range(sides+1):
            b = TAU*j/sides
            noise = 1+math.sin(a)*(.09*math.sin(3*b+centre[0])+.055*math.sin(7*b+centre[1]))
            v.append(centre+scale*np.array([math.sin(a)*math.cos(b), math.sin(a)*math.sin(b), math.cos(a)])*noise)
            uv.append([j/sides, 1-i/rings])
    bottom = len(v); v.append(centre-[0, 0, scale[2]]); uv.append([.5, 0.])
    for j in range(sides):
        f.append((0, 1+j, 2+j))
        for i in range(rings-2):
            k = 1+i*(sides+1)+j; lower = k+sides+1
            f.extend([(k, lower, k+1), (k+1, lower, lower+1)])
        k = 1+(rings-2)*(sides+1)+j; f.append((k, bottom, k+1))
    g.add(v, f, material, uv)


def _giant_tree(g, m, rng, x, y, height, index, canopy):
    z = terrain_height(x, y); p = np.array([x, y, z]); phase = rng.uniform(0, TAU)
    radius = height*rng.uniform(.046, .062)
    lean = np.array([math.cos(phase), math.sin(phase), 0])*height*.055
    pts = [p+lean*t*t+[0, 0, height*t] for t in [0, .10, .28, .49, .67, .81, .94]]
    g.tube(pts, [radius*a for a in [1.45, 1.05, .83, .61, .40, .22, .05]],
           m['bark'], segments=12, rough=.06)
    # Buttresses are visible from L4 and make these read as ancient peers.
    for j in range(7):
        a = phase+j*TAU/7; u = np.array([math.cos(a), math.sin(a), 0])
        g.tube([p+u*radius*.55+[0, 0, 12], p+u*radius*1.8+[0, 0, 2.5],
                p+u*radius*3+[0, 0, .1]], [radius*.48, radius*.32, .08],
               m['bark'], 6)
    for j in range(7):
        a = phase+j*2.39996
        direction = np.array([math.cos(a), math.sin(a), 0])
        t = .50+(j%3)*.115; start = p+lean*t*t+[0, 0, height*t]
        span = height*(.24+.033*(j%3))
        tip = p+lean*.7+direction*span+[0, 0, height*(.76+(j%3)*.065)]
        g.tube([start, start+direction*span*.48+[0, 0, height*.04], tip],
               [radius*.31, radius*.21, radius*.03], m['bark'], 7, rough=.025)
        # Each broad scaffold ends in a cluster rather than a repeated sphere.
        size = height*(.19+.018*(j%2))
        _crown(g, tip, [size*1.13, size*.93, size*.45], canopy[(index+j)%3], 14, 7)
        for k in [-1, 1]:
            q = tip + np.array([-direction[1], direction[0], .15])*size*.62*k
            q[2] += size*.13
            _crown(g, q, [size*.77, size*.70, size*.41], canopy[(index+j+(k>0))%3], 10, 5)
    top = p+lean+[0, 0, height*.94]
    _crown(g, top, [height*.19, height*.17, height*.08], canopy[index%3], 14, 7)


def _forest_tree(g, m, rng, x, y, height, tier, index, canopy, z=None):
    if z is None: z = terrain_height(x, y)
    p = np.array([x, y, z]); rad = height*rng.uniform(.28, .36)
    g.cylinder(p+[0, 0, height*.38], height*.035, height*.76, m['dark'], 5 if tier == 1 else 4, r2=height*.017)
    if index%6 == 0:
        # Scattered conifers break the repeating broadleaf skyline.
        for j in range(3 if tier == 1 else 2):
            g.cylinder(p+[0, 0, height*(.40+j*.18)], rad*(1-j*.20), height*.53,
                       canopy[index%3], 7 if tier == 1 else 5, r2=height*.015)
    else:
        count = 3 if tier == 1 else 2
        for j in range(count):
            a = index*.61+j*2.4
            q = p+[math.cos(a)*rad*.35, math.sin(a)*rad*.35, height*(.66+j*.09)]
            _crown(g, q, [rad*(1-j*.08), rad*.88, height*.25],
                   canopy[(index+j)%3], 12 if tier == 1 else 6, 6 if tier == 1 else 3)


def _forest(g, m, rng, canopy, road):
    peers = [(-118, 35, 121), (137, 105, 127), (-194, 265, 116), (222, 335, 134),
             (-265, -125, 113), (285, -102, 123), (-121, -228, 119), (215, -267, 112),
             (-423, 451, 132), (464, 468, 119), (-591, 58, 128), (608, 45, 115),
             (-401, 850, 125), (447, 941, 136), (-801, 406, 129), (790, 672, 122)]
    for index, (x, y, h) in enumerate(peers):
        g.group = 'Landscape/AncientPeers_'+('West' if x < 0 else 'East')+('_Near' if y < 380 else '_Far')
        _giant_tree(g, m, rng, x, y, h*1.42, index, canopy)
    counts = [0, 0]
    # Uneven groves leave a north view corridor and a southern sea outlook.
    # These clusters are area samples, never concentric belts or equal rows.
    groves = [(-230, 70, 250, 255, 330), (250, 130, 260, 300, 350),
              (-490, 560, 300, 365, 310), (490, 625, 290, 390, 310),
              (-980, 700, 520, 650, 390), (1030, 870, 490, 650, 390),
              (-600, 1410, 450, 480, 245), (640, 1490, 510, 500, 245)]
    for gi, (cx, cy, sx, sy, target) in enumerate(groves):
        g.group = 'Landscape/ForestGrove_%02d'%gi
        accepted = 0; attempts = 0
        while accepted < target and attempts < target*12:
            attempts += 1; a = rng.uniform(0, TAU); r = math.sqrt(rng.random())
            x = cx+math.cos(a)*r*sx; y = cy+math.sin(a)*r*sy
            d = math.hypot(x, y)
            if d < 68 or y < float(coast_y(x))+38: continue
            if math.hypot(x-CITY_CENTER[0], y-CITY_CENTER[1]) < CITY_RADIUS+40: continue
            # Preserve a legible approach, including its distant city sight line.
            if y < 610 and _road_distance(x, y, road) < (18 if y < 200 else 29): continue
            if 170 < y < 600 and abs(x) < 28+y*.035: continue
            if any(math.hypot(x-px, y-py) < 17 for px, py, _ in peers): continue
            tier = 1 if d < 650 else 2
            height = rng.uniform(13, 32) if tier == 1 else rng.uniform(17, 38)
            _forest_tree(g, m, rng, x, y, height, tier, accepted, canopy)
            accepted += 1; counts[tier-1] += 1
    return len(peers), counts


def _city_house(g, m, rng, x, y, index):
    z = 12.06; w = rng.uniform(7.5, 13.2); d = rng.uniform(8, 13.8)
    h = rng.uniform(7, 15.5); a = rng.uniform(-.14, .14)
    side = np.array([math.cos(a), math.sin(a), 0]); front = np.array([-math.sin(a), math.cos(a), 0])
    up = np.array([0, 0, 1]); p = np.array([x, y, z]); axes = [side, front, up]
    def P(xx, yy, zz): return p+side*xx+front*yy+up*zz
    wall = m['townwalls'][index%len(m['townwalls'])]
    g.box(P(0, 0, h*.5), [w, d, h], wall, axes)
    ridge = h+rng.uniform(2.0, 4.0)
    for s in [-1, 1]:
        q = [P(-w*.56, 0, ridge), P(w*.56, 0, ridge), P(w*.56, s*d*.58, h), P(-w*.56, s*d*.58, h)]
        if s < 0: q.reverse()
        g.quad(q, m['tile'], [(0, 0), (w*.15, 0), (w*.15, d*.08), (0, d*.08)])
        # Tiny warm rectangles are enough at this range; no interior geometry.
        for xx in [-w*.23, w*.23]:
            g.quad([P(xx-.64, s*(d/2+.015), h*.58), P(xx+.64, s*(d/2+.015), h*.58),
                    P(xx+.64, s*(d/2+.015), h*.58+1.6), P(xx-.64, s*(d/2+.015), h*.58+1.6)][::-s], m['city'])
    for s in [-1, 1]:
        q = [P(s*w*.5, -d*.5, h), P(s*w*.5, d*.5, h), P(s*w*.5, 0, ridge)]
        g.add(q, [(0, 1, 2)] if s > 0 else [(2, 1, 0)], wall, [(0, 0), (1, 0), (.5, 1)])


def _tower(g, material, roof, x, y, radius=7.4, height=25., z=12., conical=False):
    g.cylinder([x, y, z+height*.5], radius, height, material, 12)
    g.cylinder([x, y, z+height-.65], radius*1.16, 1.6, material, 12)
    for j in range(8):
        a = j*TAU/8; u = [math.cos(a), math.sin(a), 0]; t = [-math.sin(a), math.cos(a), 0]
        g.box([x+math.cos(a)*radius, y+math.sin(a)*radius, z+height+1.0],
              [radius*.52, 1.55, 2.1], material, [t, u, [0, 0, 1]])
    if conical: g.cylinder([x, y, z+height+5.5], radius*1.18, 11., roof, 12, r2=.15)


def _city(g, m, rng, city_stone):
    g.group = 'Landscape/FortifiedCity'; cx, cy = CITY_CENTER; radius = CITY_RADIUS
    # Radial curtain wall: an actual circular enclosure with an open south gate.
    segments = 96; thickness = 4.3; wallheight = 19.; ground = 12.
    for i in range(segments):
        a = i*TAU/segments; b = (i+1)*TAU/segments
        midpoint = (a+b)/2
        if abs(math.atan2(math.sin(midpoint+math.pi/2), math.cos(midpoint+math.pi/2))) < .078: continue
        def P(t, r, z): return [cx+r*math.cos(t), cy+r*math.sin(t), z]
        for r, outward in [(radius, True), (radius-thickness, False)]:
            q = [P(a, r, ground), P(b, r, ground), P(b, r, ground+wallheight), P(a, r, ground+wallheight)]
            if not outward: q.reverse()
            g.quad(q, city_stone, [(a*radius*.1, 0), (b*radius*.1, 0), (b*radius*.1, wallheight*.1), (a*radius*.1, wallheight*.1)])
        g.quad([P(a, radius-thickness, ground+wallheight), P(a, radius, ground+wallheight),
                P(b, radius, ground+wallheight), P(b, radius-thickness, ground+wallheight)], city_stone)
        tangent = [-math.sin(midpoint), math.cos(midpoint), 0]; radial = [math.cos(midpoint), math.sin(midpoint), 0]
        g.box(P(midpoint, radius-thickness*.5, ground+wallheight+1.2), [4.7, thickness, 2.4], city_stone,
              [tangent, radial, [0, 0, 1]])
    for j in range(12):
        a = j*TAU/12
        if j == 9: continue  # This location belongs to the double-tower gate.
        _tower(g, city_stone, m['tile'], cx+radius*math.cos(a), cy+radius*math.sin(a))
    # Gate towers flank, rather than block, the road into the city.
    for sign in [-1, 1]:
        _tower(g, city_stone, m['tile'], sign*15.5, cy-radius+1, radius=8.2, height=29, conical=True)
    g.box([0, cy-radius+1, ground+22], [17, 8, 7], city_stone)
    g.quad([[-6, cy-radius-3.1, ground+16], [6, cy-radius-3.1, ground+16],
            [6, cy-radius-3.1, ground+20.2], [-6, cy-radius-3.1, ground+20.2]], m['city'])
    # Readable arterial streets and a central civic square, not residential rings.
    g.box([0, cy, 12.035], [11, radius*1.88, .04], m['road'])
    g.box([0, cy+19, 12.035], [radius*1.86, 9, .04], m['road'])
    g.box([0, cy+8, 12.045], [67, 70, .04], m['stone'])
    count = 0
    for ix, x in enumerate(np.arange(-135, 136, 18)):
        for iy, yy in enumerate(np.arange(-135, 136, 18)):
            xx = x+rng.uniform(-1.8, 1.8); y = cy+yy+rng.uniform(-1.8, 1.8)
            if math.hypot(xx, y-cy) > radius-19: continue
            if abs(xx) < 13 or abs(y-cy-19) < 12: continue
            if abs(xx) < 37 and abs(y-cy-8) < 41: continue
            _city_house(g, m, rng, xx, y, count); count += 1
    # One tall keep and four slender turrets anchor the skyline above the roofs.
    g.box([0, cy+8, 12+18], [28, 36, 36], city_stone)
    g.box([0, cy+8, 12+37], [32, 40, 2], city_stone)
    for x in [-14, 14]:
        for y in [cy-10, cy+26]:
            _tower(g, city_stone, m['tile'], x, y, radius=4.3, height=47, conical=True)
    _tower(g, city_stone, m['tile'], 0, cy+8, radius=7.5, height=66, conical=True)
    for x in [-8, 0, 8]:
        for z in [29, 40]:
            g.quad([[x-1.1, cy-10.02, z], [x+1.1, cy-10.02, z],
                    [x+1.1, cy-10.02, z+3.8], [x-1.1, cy-10.02, z+3.8]], m['city'])
    return count, 18


def _islands(g, m, rng, canopy):
    # All six landforms descend below SEA_LEVEL. None is a floating sky island.
    islands = [(-700, -1030, 255, 138, 109), (610, -1390, 280, 165, 143),
               (-1420, -1860, 410, 220, 177), (1510, -2240, 395, 245, 213),
               (-350, -2920, 465, 235, 167), (500, -3880, 595, 275, 239)]
    trees = 0
    for idx, (cx, cy, sx, sy, height) in enumerate(islands):
        g.group = 'Landscape/SeaIsland_%02d'%idx
        n = 40 if idx < 2 else 28; rings = 10 if idx < 2 else 7
        def H(r, a):
            return SEA_LEVEL-.8+height*max(0, 1-r**1.25)**1.3*(.88+.13*math.cos(a*3+.5)+.10*math.sin(a*5+idx))
        v = [[cx, cy, SEA_LEVEL-.8+height*.88]]; uv = [[cx*.014, cy*.014]]; f = []
        for ri in range(1, rings+1):
            r = ri/rings
            for j in range(n):
                a = j*TAU/n; edge = 1+.10*math.sin(3*a+idx)+.065*math.cos(7*a-.7)
                x = cx+sx*r*math.cos(a)*edge; y = cy+sy*r*math.sin(a)*edge
                v.append([x, y, H(r, a)]); uv.append([x*.018, y*.018])
                if ri == 1: f.append((0, 1+j, 1+(j+1)%n))
                else:
                    k = 1+(ri-1)*n+j; kn = 1+(ri-1)*n+(j+1)%n
                    f.extend([(k-n, k, kn), (k-n, kn, kn-n)])
        # Stone shoreline and forested interior use the same watertight surface.
        inner, outer = [], []
        for tri in f:
            (inner if np.mean([v[j][2] for j in tri]) > 15 else outer).append(tri)
        g.add(v, outer, m['stone'], uv); g.add(v, inner, m['terrain'], uv)
        for j in range(31 if idx < 2 else 19):
            a = rng.uniform(0, TAU); r = rng.uniform(.20, .74)
            edge = 1+.10*math.sin(3*a+idx)+.065*math.cos(7*a-.7)
            x = cx+sx*r*math.cos(a)*edge; y = cy+sy*r*math.sin(a)*edge
            _forest_tree(g, m, rng, x, y, rng.uniform(16, 28), 2, j, canopy, H(r, a)-2)
            trees += 1
    return len(islands), trees


def _mountain_height(x, y):
    # Overlapping asymmetric ridge masses, sampled into one surface, avoid
    # disconnected cone props and preserve saddles between the seven summits.
    peaks = [(-2000, 2600, 590, 1100, 1000), (-1320, 2250, 670, 920, 780),
             (-660, 2590, 830, 1050, 1000), (-160, 2170, 560, 680, 780),
             (470, 2510, 790, 1040, 920), (1220, 2380, 700, 860, 840),
             (2020, 2780, 730, 1100, 1150)]
    h = 0.
    for i, (cx, cy, height, sx, sy) in enumerate(peaks):
        dx, dy = (x-cx)/sx, (y-cy)/sy
        dx -= .17*math.sin(dy*2.3+i*.7)
        angle = math.atan2(dy, dx)
        d = math.hypot(dx, dy)/(1+.19*math.sin(3*angle+i)+.10*math.cos(5*angle-i*.6))
        main = height*max(0, 1-d**.92)
        # Off-axis shoulders and smaller spurs interrupt the cone profiles.
        shoulder = math.hypot((x-cx-sx*.30)/(.57*sx), (y-cy+sy*.20)/(.60*sy))
        spur = height*.61*max(0, 1-shoulder**.86)
        h = max(h, main, spur)
    rough = (24*math.sin(x*.012+y*.015)+13*math.sin(x*.035-y*.018))
    h += rough*min(h/180, 1)
    foothill = 92*max(0, 1-abs(y-2100)/1100)*(1+.22*math.sin(x*.004))
    edge = min(1., max(0., (y-1240)/220.))*min(1., max(0., (3860-y)/340.))
    edge *= min(1., max(0., (3000-abs(x))/320.))
    return terrain_height(x, y)-1.0 + (h+foothill)*edge


def _clip_snow(points, values, positive):
    out = []
    for p, q, a, b in zip(points, points[1:]+points[:1], values, values[1:]+values[:1]):
        inside, next_inside = (a >= 0), (b >= 0)
        if not positive: inside, next_inside = not inside, not next_inside
        if inside: out.append(p)
        if inside != next_inside: out.append(p+(q-p)*(a/(a-b)))
    return out


def _mountains(g, rock, snow, snowshade):
    xs = np.linspace(-3000, 3000, 105); ys = np.linspace(1240, 3860, 50)
    groups = 4
    for sector in range(groups):
        g.group = 'Landscape/SnowRange_%d'%sector
        start, end = sector*26, (sector+1)*26
        mesh = {rock: ([], [], []), snow: ([], [], []), snowshade: ([], [], [])}
        def add_poly(poly, material):
            if len(poly) < 3: return
            vv, ff, uv = mesh[material]; k = len(vv)
            vv.extend(poly); uv.extend([[p[0]*.012, p[1]*.012] for p in poly])
            ff.extend([(k, k+i, k+i+1) for i in range(1, len(poly)-1)])
        for ix in range(start, end):
            for iy in range(len(ys)-1):
                xy = [(xs[ix], ys[iy]), (xs[ix+1], ys[iy]),
                      (xs[ix+1], ys[iy+1]), (xs[ix], ys[iy+1])]
                q = [np.array([x, y, _mountain_height(x, y)]) for x, y in xy]
                for indices in [(0, 1, 2), (0, 2, 3)]:
                    tri = [q[i] for i in indices]
                    vals = [p[2]-(310+12*math.sin(p[0]*.003)+5*math.cos(p[1]*.003)) for p in tri]
                    add_poly(_clip_snow(tri, vals, False), rock)
                    normal = np.cross(tri[1]-tri[0], tri[2]-tri[0])
                    snowy = snowshade if normal[1] > abs(normal[2])*.68 and sum(p[1] for p in tri)/3 > 2250 else snow
                    add_poly(_clip_snow(tri, vals, True), snowy)
        for material, (v, f, uv) in mesh.items():
            if f:
                # Share vertices after snow-line clipping so generated normals
                # flow over the slopes, rather than facet every sampling cell.
                vv = np.asarray(v); ff = np.asarray(f)
                _, index, inverse = np.unique(np.round(vv, 6), axis=0, return_index=True, return_inverse=True)
                vv = vv[index]; ff = inverse[ff]
                area = np.linalg.norm(np.cross(vv[ff[:, 1]]-vv[ff[:, 0]], vv[ff[:, 2]]-vv[ff[:, 0]]), axis=1)
                g.add(vv, ff[area > 1e-8], material, np.asarray(uv)[index])
    return 7, groups


def landscape(g, m, rng):
    """Build an economical asymmetric mainland panorama and return manifest data."""
    before = sum(len(b['f']) for b in g.batches.values())
    # Existing source textures are reused. No new textures, alpha materials,
    # downloaded assets, realtime lights, or external dependencies are needed.
    canopy = [g.material('ForestCanopyPeer%d'%i, color, roughness=.96)
              for i, color in enumerate([(.17, .29, .135), (.23, .34, .165), (.12, .235, .155)])]
    city_stone = g.material('CityLimestone', (.68, .68, .55), 'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1)
    road_mat = g.material('RoadEarth', (.50, .40, .255), 'tile_clay.png', roughness=1)
    alpine = g.material('AlpineRock', (.31, .36, .40), 'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1)
    snow = g.material('AlpineSnow', (.88, .93, .97), roughness=.92)
    snowshade = g.material('AlpineSnowShade', (.60, .72, .82), roughness=.95)

    terrain_sectors = _land(g, m)
    _original_root_bed(g, m['stone'])
    _sea(g, m)
    road = road_points(); g.group = 'Landscape/NorthRoad'
    _ribbon(g, road, 10.6, m['stone'], .08)
    _ribbon(g, road, 7.4, road_mat, .13)
    # A few milestones and one roadside outpost establish the road's scale.
    for i in [22, 48, 77]:
        if i >= len(road)-1: continue
        p = road[i]; delta = road[i+1]-road[i]
        side = np.array([-delta[1], delta[0]])/np.linalg.norm(delta); xy = p+side*6.3
        z = terrain_height(*xy)
        g.box([*xy, z+.75], [.65, .65, 1.5], m['stone'])
    peers, forest_tiers = _forest(g, m, rng, canopy, road)
    houses, towers = _city(g, m, rng, city_stone)
    islands, island_trees = _islands(g, m, rng, canopy)
    peaks, mountain_sectors = _mountains(g, alpine, snow, snowshade)
    after = sum(len(b['f']) for b in g.batches.values())
    return {
        'distantHouses': houses, 'forestTrees': peers+sum(forest_tiers)+island_trees,
        'giantPeerTrees': peers, 'forestNearTrees': forest_tiers[0], 'forestFarTrees': forest_tiers[1],
        'islandTrees': island_trees, 'terrainSectors': terrain_sectors,
        'forestCrownSides': 12, 'forestCrownRings': 6, 'coastRoadBands': 0, 'templeStoreys': 0,
        'walledCities': 1, 'cityCenter': list(CITY_CENTER), 'cityWallRadius': CITY_RADIUS,
        'cityTowers': towers, 'northRoadLength': round(float(np.linalg.norm(np.diff(road, axis=0), axis=1).sum()), 2),
        'seaIslands': islands, 'snowPeaks': peaks, 'mountainSectors': mountain_sectors,
        'landscapeTriangles': after-before, 'landscapeNewMaterials': 8,
        'visualProfile': 'Windows50_FantasyMainland',
        'landscapeDirections': {'city': 'north/+Y', 'snowRange': 'north/+Y beyond city', 'sea': 'south/-Y'},
        'groundColliderOwner': 'build_world', 'sceneryCoordinates': 'X east, Y north, Z up',
    }
