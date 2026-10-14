"""Additive, shared-texture art pass for the fantasy mainland scenery.

Call add_scenery_detail(g, M, rng) immediately after landscape(), before
Geometry.compact(). No collisions, near shops, root-bed or traversal are edited.
"""
import math
import numpy as np

TAU = math.tau


def _primitive_ranges(faces):
    """Recover consecutive closed primitives in the authored canopy batches.

    Each crown/tapered conifer was appended as one indexed component. New
    component indices exceed the running maximum of all previous triangles.
    Unlike position clustering this also preserves touching or overlapping crowns.
    """
    f = np.asarray(faces, dtype=np.int64)
    if not len(f): return
    highest = np.maximum.accumulate(f.max(axis=1))
    starts = np.r_[0, np.where(f[1:].min(axis=1) > highest[:-1])[0]+1]
    ends = np.r_[starts[1:], len(f)]
    for start, end in zip(starts, ends):
        part = f[start:end]
        yield int(part.min()), int(part.max())+1, part


def _canopy_detail(g, m, rng, spray_materials):
    candidates = []
    removed_core_triangles = 0
    viewer = np.array([0., 0., 48.])
    # Snapshot first; new detail batches must never become input candidates.
    for (group, material), batch in list(g.batches.items()):
        if not group.startswith(('Landscape/AncientPeers_', 'Landscape/ForestGrove_')): continue
        if not material.startswith('ForestCanopyPeer'): continue
        vertices = np.asarray(batch['v'])
        remove_vertex = np.zeros(len(vertices), dtype=bool)
        for low, high, f in _primitive_ranges(batch['f']):
            v = vertices[low:high]; centre = (v.max(axis=0)+v.min(axis=0))*.5
            radius = np.linalg.norm(centre[:2])
            if radius > 430 or radius < 48: continue
            extent = v.max(axis=0)-v.min(axis=0)
            if min(extent[:2]) < 4 or extent[2] > max(extent[:2])*1.7: continue
            q = vertices[f]; normals = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])
            area = np.linalg.norm(normals, axis=1)*.5
            normals /= np.maximum(area[:, None]*2, 1e-9)
            centres = q.mean(axis=1)
            view = viewer-centres; view /= np.linalg.norm(view, axis=1)[:, None]
            # Concentrate detail on upper/outer visible surfaces; do not fill
            # hidden interiors with alpha layers. The back receives sparse tips.
            high_view = np.array([-20., -40., 135.])-centres
            high_view /= np.linalg.norm(high_view, axis=1)[:, None]
            visibility = np.clip(np.maximum(np.sum(normals*view, axis=1), np.sum(normals*high_view, axis=1))+.35, .10, 1.)
            weight = area*visibility
            giant = group.startswith('Landscape/AncientPeers_')
            scale = rng.uniform(2.2, 3.3) if giant else rng.uniform(1.15, 1.85)
            leaf_defined = giant or radius < 230
            if giant:
                count = min(360, max(90, int(weight.sum()/(scale*scale)*1.05)))
            elif leaf_defined:
                count = min(150, max(80, int(weight.sum()/(scale*scale)*1.75)))
            elif radius < 330:
                count = 25
            else:
                count = 5
            candidates.append((group, q, normals, weight, scale, count, giant, centre, leaf_defined))
            if leaf_defined:
                remove_vertex[low:high] = True
            else:
                core_scale = .60 if radius < 330 else .925
                vertices[low:high] = centre+(vertices[low:high]-centre)*core_scale
        ff = np.asarray(batch['f'])
        keep_faces = ~remove_vertex[ff[:, 0]]
        removed_core_triangles += int((~keep_faces).sum())
        keep_vertices = ~remove_vertex
        remap = np.cumsum(keep_vertices)-1
        batch['v'] = vertices[keep_vertices].tolist()
        batch['uv'] = np.asarray(batch['uv'])[keep_vertices].tolist()
        batch['f'] = remap[ff[keep_faces]].tolist()
        if 'colors' in batch: batch['colors'] = np.asarray(batch['colors'])[keep_vertices]
    requested = sum(c[5] for c in candidates)
    budget_scale = min(1., 90000/max(requested, 1))
    cards = twigs = peer_cards = peer_crowns = leaf_crowns = 0
    for group, q, normals, weight, scale, count, giant, centre, leaf_defined in candidates:
        count = max(3, int(count*budget_scale))
        if giant: peer_crowns += 1
        if leaf_defined: leaf_crowns += 1
        group_id = ('Peer_'+group[len('Landscape/AncientPeers_'):]) if giant else ('Grove_'+group.rsplit('_', 1)[1])
        g.group = 'Landscape/DetailLeaves_'+group_id
        selected = rng.choice(len(q), size=count, p=weight/weight.sum())
        for j, ti in enumerate(selected):
            u, v = rng.random(2)
            if u+v > 1: u, v = 1-u, 1-v
            p = q[ti, 0]+u*(q[ti, 1]-q[ti, 0])+v*(q[ti, 2]-q[ti, 0])
            normal = normals[ti]
            if leaf_defined:
                # Fill a leaf volume instead of decorating the surface of a
                # solid balloon. Overlapping sprays now own the silhouette.
                p = centre+(p-centre)*rng.uniform(.70, 1.055)
            reference = np.array([0., 0., 1.]) if abs(normal[2]) < .85 else np.array([1., 0., 0.])
            right = np.cross(reference, normal); right /= np.linalg.norm(right)
            up = np.cross(normal, right)
            angle = rng.uniform(0, TAU)
            tangent = right*math.cos(angle)+up*math.sin(angle)
            along = -right*math.sin(angle)+up*math.cos(angle)
            size = scale*rng.uniform(1.45, 2.25)
            # A slight cant plus separate twig ends avoids wrapping the crown
            # in a visibly continuous translucent shell.
            p += normal*rng.uniform(.03, .12)*size
            r = tangent*size*.58
            a = (along+normal*rng.uniform(-.20, .35))*size*.72
            g.quad([p-r-a, p+r-a, p+r+a, p-r+a], spray_materials[(cards+j)%len(spray_materials)], [(0, 0), (2, 0), (2, 2), (0, 2)])
            cards += 1
            if giant: peer_cards += 1
            if leaf_defined and j%24 == 11:
                g.group = 'Landscape/DetailTwigs_'+group_id
                root = p-along*size*.78-normal*size*.32
                tip = p+along*size*.69
                g.tube([root, p-normal*size*.16, tip], [.072 if giant else .034, .030 if giant else .017, .004], m['bark'], 5)
                twigs += 1
                if j%96 == 11:
                    fork = p+tangent*size*.62+along*size*.16
                    g.tube([p-normal*size*.15, fork], [.035 if giant else .017, .003], m['bark'], 4)
                    twigs += 1
                g.group = 'Landscape/DetailLeaves_'+group_id
    return len(candidates), cards, twigs, peer_crowns, peer_cards, leaf_crowns, removed_core_triangles


def _arch_wedge(g, cx, cy, cz, inner, outer, start, end, depth, material):
    # Four curved-ring points at the front, extruded backwards into the wall.
    p = []
    for radius, angle in [(inner, start), (outer, start), (outer, end), (inner, end)]:
        p.append([cx+radius*math.cos(angle), cy, cz+radius*math.sin(angle)])
    v = p+[[x, y+depth, z] for x, y, z in p]
    f = [(0, 1, 2), (0, 2, 3), (6, 5, 4), (7, 6, 4)]
    for i in range(4):
        j = (i+1)%4
        f.extend([(i, i+4, j+4), (i, j+4, j)])
    g.add(v, f, material, [[x*.15, z*.15] for x, _, z in v])


def _remove_gate_light(g, material):
    """Remove only the old unrealistic luminous rectangle over the gate.

    This is a tightly identified four-vertex quad within one distant batch;
    near-world lights and all other city windows remain untouched.
    """
    key = ('Landscape/FortifiedCity', material)
    if key not in g.batches: return 0
    batch = g.batches[key]; v = np.asarray(batch['v']); f = np.asarray(batch['f'])
    q = v[f]
    match = (np.max(np.abs(q[:, :, 1]-574.9), axis=1) < .005)
    match &= (np.max(np.abs(q[:, :, 0]), axis=1) <= 6.001)
    match &= (np.min(q[:, :, 2], axis=1) >= 27.99) & (np.max(q[:, :, 2], axis=1) <= 32.21)
    batch['f'] = f[~match].tolist()
    return int(match.sum())


def _city_detail(g, m, rng, masonry, mortar, banner):
    cx, cy, radius, base = 0., 740., 162., 12.
    g.group = 'Landscape/DetailCityMasonry'
    stones = 0
    # Slightly inset joints between individually toned ashlar courses. No giant
    # brick texture is stretched over the entire curved curtain wall.
    count = 192
    for row in range(7):
        z0 = base+row*2.68+.055; z1 = min(base+18.9, z0+2.58)
        if z1 <= z0: continue
        for i in range(count):
            a = (i+.5*(row%2))*TAU/count+.0010
            b = (i+1+.5*(row%2))*TAU/count-.0010
            mid = (a+b)*.5
            gate_angle = abs(math.atan2(math.sin(mid+math.pi/2), math.cos(mid+math.pi/2)))
            if gate_angle < .088: continue
            rr = radius+.028
            q = [[rr*math.cos(a), cy+rr*math.sin(a), z0], [rr*math.cos(b), cy+rr*math.sin(b), z0],
                 [rr*math.cos(b), cy+rr*math.sin(b), z1], [rr*math.cos(a), cy+rr*math.sin(a), z1]]
            g.quad(q, masonry[(i+row*3)%len(masonry)], [(0, 0), ((b-a)*rr*.15, 0), ((b-a)*rr*.15, .39), (0, .39)])
            stones += 1
    for z in [base+1.2, base+15.0, base+18.25]:
        # Projecting stone string courses cast the horizontal scale cues.
        for i in range(96):
            a, b = i*TAU/96, (i+1)*TAU/96; mid = (a+b)/2
            if abs(math.atan2(math.sin(mid+math.pi/2), math.cos(mid+math.pi/2))) < .085: continue
            radial = np.array([math.cos(mid), math.sin(mid), 0]); tangent = np.array([-radial[1], radial[0], 0])
            g.box([radial[0]*(radius+.24), cy+radial[1]*(radius+.24), z], [(b-a)*radius+.1, .58, .48], masonry[1], [tangent, radial, [0, 0, 1]])
    removed = _remove_gate_light(g, m['city'])
    g.group = 'Landscape/DetailCityGate'
    for i in range(17):
        _arch_wedge(g, 0, 574.73, 23.1, 6.65, 8.35, i*math.pi/17+.005, (i+1)*math.pi/17-.005, 5.25, masonry[i%len(masonry)])
    for sign in [-1, 1]:
        for i in range(4):
            g.box([sign*7.49, 577.35, 13.35+i*2.61], [1.6, 5.3, 2.51], masonry[(i+1)%3])
        # Hanging wrought iron lamps, two warm points instead of a glowing sign.
        p = np.array([sign*9.1, 573.9, 22.7])
        g.beam(p, p+[0, -.9, .2], .14, m['iron'])
        g.box(p+[0, -1.0, -.6], [.78, .66, 1.32], m['iron'])
        g.box(p+[0, -1.345, -.6], [.54, .025, .94], m['city'])
    # Narrow arrow slits and masonry collars articulate the circular towers.
    towers = []
    for j in range(12):
        if j == 9: continue
        a = j*TAU/12; towers.append((radius*math.cos(a), cy+radius*math.sin(a), 7.4, 25., a))
    towers.extend([(-15.5, cy-radius+1, 8.2, 29., -math.pi/2), (15.5, cy-radius+1, 8.2, 29., -math.pi/2)])
    for ti, (x, y, rr, hh, outward) in enumerate(towers):
        g.group = 'Landscape/DetailCityTowers'
        for z in [base+2.2, base+hh*.52, base+hh-2.3]:
            g.cylinder([x, y, z], rr+.12, .45, masonry[1], 12)
        for a in [outward-.52, outward, outward+.52]:
            radial = np.array([math.cos(a), math.sin(a), 0]); tangent = np.array([-radial[1], radial[0], 0]); up = np.array([0, 0, 1])
            p = np.array([x, y, base+hh*.59])+radial*(rr+.06)
            g.quad([p-tangent*.21-up*1.35, p+tangent*.21-up*1.35, p+tangent*.21+up*1.35, p-tangent*.21+up*1.35], mortar)
            if ti%3 == 0 and a == outward:
                p = p-up*3.2+radial*.14
                # Banners are static at this distance and share the woven map.
                q = [p-tangent*1.05, p+tangent*1.05, p+tangent*.82-up*5.8, p-up*6.4, p-tangent*.82-up*5.8]
                g.add(q, [(0, 1, 2), (0, 2, 3), (0, 3, 4)], banner, [(0, 1), (1, 1), (1, .15), (.5, 0), (0, .15)])
    # Read back the actual seed-dependent house boxes rather than rebuilding a
    # second, mismatched town plan. Each house contributes 24 box + 6 gable verts.
    houses = 0
    for wall in m['townwalls']:
        batch = g.batches.get(('Landscape/FortifiedCity', wall))
        if not batch: continue
        v = np.asarray(batch['v'])
        if len(v)%30: continue  # A future house format must be handled explicitly.
        for house in v.reshape((-1, 30, 3)):
            centre = house[:24].mean(axis=0); z0 = house[:24, 2].min(); z1 = house[:24, 2].max()
            g.group = 'Landscape/DetailCityRoofs'
            # Front and rear fascia, projecting ridge caps, and chimney pots.
            for a, b in [(house[10], house[11]), (house[18], house[19]), (house[26], house[29])]:
                d = b-a; g.beam(a-d*.04+[0, 0, .05], b+d*.04+[0, 0, .05], .28, m['dark'])
            if houses%4 == 0:
                p = (house[26]+house[29])*.5; p[0] += 1.2; p[1] += 1.9; p[2] -= .35
                g.box(p+[0, 0, 1.2], [1.05, 1.0, 2.4], masonry[houses%3])
                g.box(p+[0, 0, 2.45], [1.3, 1.25, .30], mortar)
            # Timber eave brackets cast small but coherent scale shadows.
            for a, b in [(house[10], house[11]), (house[18], house[19])]:
                for t in [.15, .5, .85]:
                    p = a+(b-a)*t
                    g.beam(p+[0, 0, -.8], p+[0, 0, .06], .15, m['dark'])
            houses += 1
    return stones, houses, removed


def _coastal_detail(g, m, rng, cliff, pale, foam):
    faces = bands = foam_segments = 0
    for island in range(6):
        group = 'Landscape/SeaIsland_%02d'%island
        batch = g.batches.get((group, m['stone']))
        if not batch: continue
        v = np.asarray(batch['v']); n = 40 if island < 2 else 28
        centre = v[0].copy(); edge = v[-n:]; inland = v[-3*n:-2*n]
        g.group = 'Landscape/DetailIslandCliffs_%02d'%island
        for j in range(n):
            k = (j+1)%n
            # More exposed strata on the sea-facing north/west coast, with
            # sheltered gaps and beaches rather than an identical rock ring.
            radial = (edge[j,:2]+edge[k,:2])*.5-centre[:2]
            toward_world = -centre[:2]/np.linalg.norm(centre[:2])
            exposure = np.dot(radial/np.linalg.norm(radial), toward_world)
            if exposure < -.45 or (j+island)%7 == 0: continue
            a = edge[j].copy(); b = edge[k].copy()
            a[:2] = centre[:2]+(a[:2]-centre[:2])*1.018
            b[:2] = centre[:2]+(b[:2]-centre[:2])*1.018
            a[2] = b[2] = -4.85
            ta, tb = inland[j].copy(), inland[k].copy()
            # Narrow crags rise out of existing slopes and join below water.
            ta[2] += rng.uniform(2, 10); tb[2] += rng.uniform(2, 10)
            ma = a*.68+ta*.32; mb = b*.68+tb*.32
            ma[2] = ta[2]*.68-1.3; mb[2] = tb[2]*.68-1.3
            vertices = [a, b, mb, ma, ta, tb]
            triangles = [(0, 1, 2), (0, 2, 3), (3, 2, 5), (3, 5, 4)]
            # Outward face winding follows the coastline's CCW radial order.
            g.add(vertices, triangles, cliff, [[p[0]*.14, p[2]*.18] for p in vertices]); faces += 4
            for t in [.29, .57, .81]:
                p = a+(ta-a)*t; q = b+(tb-b)*t
                # Raised, discontinuous limestone layers follow the cliff face.
                p[2] += .12; q[2] += .12
                g.quad([p, q, q+[0, 0, .35], p+[0, 0, .35]], pale); bands += 1
            # Small angular talus ribs break the coastline without giant rocks.
            if j%3 == 0:
                c = (ma+mb)*.5; foot = (a+b)*.5
                width = np.linalg.norm(a[:2]-b[:2])*.12
                tangent = b-a; tangent[2] = 0; tangent /= np.linalg.norm(tangent)
                vv = [foot-tangent*width, foot+tangent*width, c+[0, 0, 4], ta, tb]
                g.add(vv, [(0, 1, 2), (0, 2, 3), (2, 1, 4), (3, 2, 4)], m['stone'], [[p[0]*.15, p[2]*.15] for p in vv]); faces += 4
            # Broken opaque foam strips sit slightly above the water crests;
            # there is no second transparent water plane and no alpha blending.
            g.group = 'Landscape/DetailShoreFoam_%02d'%island
            for start, end in [(.05, .34), (.49, .90)]:
                p = a+(b-a)*start; q = a+(b-a)*end
                p[2] = q[2] = -3.88
                out = (p+q)*.5-centre; out[2] = 0; out /= np.linalg.norm(out)
                width = rng.uniform(.6, 1.6)
                g.quad([p, p+out*width, q+out*width, q], foam); foam_segments += 1
            g.group = 'Landscape/DetailIslandCliffs_%02d'%island
    return faces, bands, foam_segments


def add_scenery_detail(g, M, rng):
    """Apply an art-detail pass and return manifest-ready counts.

    Nearby opaque foliage cores are replaced by overlapping cutout sprays.
    The distant gate's luminous sign is replaced by masonry and small lanterns.
    """
    before = sum(len(b['f']) for b in g.batches.values())
    sprays = [g.material('FoliageScenerySpray%d'%i, col, 'foliage_spray.png', roughness=.91,
                         shader='Foliage', alphaClip=.42)
              for i, col in enumerate([(.84, .96, .73), (.95, 1.0, .81), (.73, .90, .76)])]
    masonry = [g.material('CityAshlar%d'%i, col, 'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1,
                           normal='PBR/rocky_terrain_02_nor_gl_2k.jpg', uvScale=.8)
               for i, col in enumerate([(.62, .62, .51), (.75, .74, .61), (.55, .57, .49)])]
    mortar = g.material('CityRecess', (.14, .16, .145), roughness=1)
    banner = g.material('CityWovenBanner', (.49, .145, .08), 'woven.png', roughness=1)
    cliff = g.material('CoastalStrata', (.48, .54, .51), 'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1,
                       normal='PBR/rocky_terrain_02_nor_gl_2k.jpg', uvScale=.8)
    pale = g.material('CoastalPaleStrata', (.60, .63, .56), 'PBR/rocky_terrain_02_diff_4k.jpg', roughness=1)
    foam = g.material('CoastalFoam', (.52, .62, .61), roughness=.8)
    # Shared scan used as distant macro/micro surface breakup, kept dark under
    # the leaf cards. This is a material proxy, not a claim of scanned foliage.
    for i, color in enumerate([(.23, .35, .17), (.30, .40, .20), (.19, .32, .20)]):
        key = 'ForestCanopyPeer%d'%i
        if key in g.materials:
            g.materials[key].update(color=list(color), texture='PBR/rocky_terrain_02_diff_4k.jpg',
                                    normal='PBR/rocky_terrain_02_nor_gl_2k.jpg', uvScale=14, normalScale=.25)
    crowns, cards, twigs, peer_crowns, peer_cards, leaf_crowns, removed_cores = _canopy_detail(g, M, rng, sprays)
    stones, houses, removed = _city_detail(g, M, rng, masonry, mortar, banner)
    cliff_faces, strata, foam_segments = _coastal_detail(g, M, rng, cliff, pale, foam)
    # Preserve the approved legacy centimetre quantization for leaf cards.
    # It reduced compressed source size, but is NOT uniformly subpixel:
    # expanded crown routes include a sampled eye only 10.83 m from a peer
    # spray vertex. Near/Far names are culling labels, not distance guarantees.
    # Keep twigs/masonry at full precision; any precision change needs its own
    # measured distance envelope and exact protected-payload revision.
    for key, batch in g.batches.items():
        if key[0].startswith('Landscape/DetailLeaves_'):
            batch['v'] = np.round(np.asarray(batch['v']), 2).tolist()

    # Whole nearby crown batches can become empty after core replacement.
    # Drop them before Geometry.compact()/bake_mood(), which expect N x 3 data.
    for key in list(g.batches):
        if key[0].startswith(('Landscape/AncientPeers_', 'Landscape/ForestGrove_')) and not len(g.batches[key]['f']):
            del g.batches[key]
    after = sum(len(b['f']) for b in g.batches.values())
    return {'sceneryDetailTriangles': after-before, 'detailedCrowns': crowns,
            'sceneryLeafSprays': cards, 'sceneryTwigs': twigs,
            'detailedPeerCrowns': peer_crowns, 'peerLeafSprays': peer_cards,
            'leafDefinedCrowns': leaf_crowns, 'removedNearCoreTriangles': removed_cores, 'cityAshlarBlocks': stones,
            'detailedCityRoofs': houses, 'replacedGateLightTriangles': removed,
            'coastalCliffFaces': cliff_faces, 'coastalStrataBands': strata,
            'coastalFoamSegments': foam_segments, 'sceneryDetailNewTextures': 0,
            'sceneryDetailNewMaterials': 11}
