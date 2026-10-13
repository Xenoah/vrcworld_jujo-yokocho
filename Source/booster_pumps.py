"""Visible fictional multistage water-boosting plant for the raised alley.

Call after apply_altitude_profile and before Geometry.compact. This module is
an environment prop, not an engineered or certified water installation. It
makes no pressure, capacity, flow, potable-water or structural safety claims.
All coordinates are source XYZ in metres, Z up. No collision or runtime code.
"""
from __future__ import annotations

import math
import numpy as np
from tree_infrastructure import _rounded_route

UP = np.array([0., 0., 1.])
BOOSTER_Z = (52., 102.)
TANK_DECK_Z = 155.
TRIANGLE_BUDGET = 30000


def route_at_height(route, z):
    """Interpolate the ACTUAL remapped riser, never the obsolete trunk formula."""
    points = np.asarray(route['points'], dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('Water riser needs finite XYZ points')
    if np.any(np.diff(points[:, 2]) <= 0):
        raise ValueError('Water riser must rise strictly monotonically')
    if z < points[0, 2]-1e-8 or z > points[-1, 2]+1e-8:
        raise ValueError('Requested booster height is outside the supplied riser')
    return np.array([np.interp(z, points[:, 2], points[:, 0]),
                     np.interp(z, points[:, 2], points[:, 1]), float(z)])


def add_booster_pumps(g, M, infrastructure):
    """Append pumps, checked branch pipes, braced skids and an upper receiver.

    infrastructure must already be altitude-transformed, with Trunk_water
    extending to Z152 and Ground_water connected at the unchanged root. Return
    plain-JSON metadata; the caller may store it at manifest['boosterPumps'].
    Existing utility routes and materials are left unchanged.
    """
    if not infrastructure:
        raise ValueError('Booster pumps require existing water infrastructure')
    by_id = {r['id']: r for r in infrastructure['utilityRoutes']}
    riser, ground = by_id['Trunk_water'], by_id['Ground_water']
    if abs(riser['points'][-1][2]-152.) > .001:
        raise ValueError('Apply the +100 m legacy altitude profile before adding boosters')
    if not np.allclose(ground['points'][-1], riser['points'][0], atol=1e-8):
        raise ValueError('Existing ground water and trunk riser endpoints are disconnected')
    if any(group.startswith('Infrastructure/Boosters/') for group, _ in g.batches):
        raise ValueError('Booster pumps have already been authored')

    old_group = g.group
    keys_before = set(g.batches)
    triangles_before = sum(len(b['f']) for b in g.batches.values())
    materials_before = set(g.materials)
    steel = 'UtilityGalvanized' if 'UtilityGalvanized' in g.materials else M['iron']
    water = 'UtilityWaterBlue' if 'UtilityWaterBlue' in g.materials else M['iron']
    copper = 'UtilityCopper' if 'UtilityCopper' in g.materials else M['trim']
    motor = g.material('BoosterMotorTeal', [.035, .19, .20], roughness=.54, metallic=.64)
    amber = g.material('BoosterZoneAmber', [.83, .51, .09], roughness=.58, metallic=.24)
    gauge_face = g.material('BoosterGaugeFace', [.80, .85, .80], roughness=.78)
    dark = M['iron']
    routes, supports, stations, valves = [], [], [], []
    counts = {'multistagePumps': 0, 'impellerStackBands': 0, 'checkValves': 0,
              'isolationWheels': 0, 'pressureGauges': 0, 'supportedStations': 0}

    def tube(identifier, points, radius=.11, material=None, rounded=True, segments=10):
        points = [np.asarray(p, dtype=float) for p in points]
        if rounded and len(points) > 2:
            points = _rounded_route(points, bend=.22)
        g.tube(points, [radius]*len(points), material or water, segments)
        routes.append({'id': identifier, 'points': [p.tolist() for p in points],
                       'radius': radius, 'kind': 'water'})
        return points

    def ring(center, radius, normal, tangent, thickness=.022, material=None):
        # Vertical handwheel in the tangent/UP plane.
        center = np.asarray(center)
        p = [center+tangent*(radius*math.cos(a))+UP*(radius*math.sin(a))
             for a in np.linspace(0, math.tau, 17)]
        g.tube(p, [thickness]*len(p), material or copper, 6)
        for along in (tangent, UP):
            g.beam(center-along*radius, center+along*radius, thickness, material or copper)
        g.beam(center-normal*.08, center+normal*.08, .038, steel)

    def flange(center, axis=UP, radius=.15):
        center, axis = np.asarray(center), np.asarray(axis)
        g.tube([center-axis*.047, center+axis*.047], [radius]*2, steel, 12)
        # Bolt heads stay low-poly and read well at the mid-range service views.
        reference = np.array([1., 0., 0.]) if abs(axis[2]) > .9 else UP
        a = np.cross(axis, reference); a /= np.linalg.norm(a)
        b = np.cross(axis, a)
        for angle in np.linspace(0, math.tau, 4, endpoint=False):
            p = center+(a*math.cos(angle)+b*math.sin(angle))*(radius*.75)
            g.tube([p-axis*.057, p+axis*.057], [.024]*2, dark, 6)

    def check_valve(identifier, p, normal, tangent):
        p = np.asarray(p)
        g.cylinder(p, .19, .30, steel, 12)
        g.cylinder(p+UP*.18, .16, .075, copper, 12)
        # Cast directional arrow is geometry, so there is no new label texture.
        a = p+normal*.205
        g.beam(a-UP*.08, a+UP*.075, .035, amber)
        g.beam(a+UP*.075, a-UP*.005+tangent*.063, .035, amber)
        g.beam(a+UP*.075, a-UP*.005-tangent*.063, .035, amber)
        flange(p-UP*.20); flange(p+UP*.235)
        valves.append({'id': identifier, 'type': 'check', 'position': p.tolist(),
                       'indicatedDirection': UP.tolist()})
        counts['checkValves'] += 1

    def isolation(identifier, p, normal, tangent):
        p = np.asarray(p)
        g.cylinder(p, .16, .22, water, 10)
        g.beam(p, p+normal*.34, .057, steel)
        ring(p+normal*.38, .18, normal, tangent)
        valves.append({'id': identifier, 'type': 'isolation', 'position': p.tolist()})
        counts['isolationWheels'] += 1

    def gauge(p, normal, tangent):
        p = np.asarray(p)
        g.beam(p-UP*.22, p, .035, copper)
        g.tube([p-normal*.055, p+normal*.055], [.145]*2, steel, 16)
        q = p+normal*.063
        g.tube([q-normal*.003, q+normal*.003], [.123]*2, gauge_face, 16)
        for a in np.linspace(-.75*math.pi, .75*math.pi, 7):
            d = tangent*math.sin(a)+UP*math.cos(a)
            g.beam(q+d*.092, q+d*.114, .007, dark)
        g.beam(q, q+tangent*.060+UP*.063, .012, dark)
        counts['pressureGauges'] += 1

    def pump(identifier, base, normal, tangent):
        """Stacked centrifugal stages below a large finned electric motor."""
        base = np.asarray(base)
        g.box(base+UP*.10, [.62, .62, .20], dark, [tangent, normal, UP])
        g.cylinder(base+UP*.33, .27, .33, water, 16)
        g.cylinder(base+UP*1.05, .235, 1.20, steel, 16)
        for z in np.linspace(.49, 1.59, 10):
            g.cylinder(base+UP*z, .257, .055, water, 12)
            counts['impellerStackBands'] += 1
        for side in (-1, 1):
            for front in (-1, 1):
                p = base+tangent*(side*.205)+normal*(front*.205)
                g.beam(p+UP*.36, p+UP*1.77, .026, copper)
                g.cylinder(p+UP*1.78, .043, .05, steel, 6)
        g.cylinder(base+UP*1.77, .29, .14, steel, 16)
        g.cylinder(base+UP*2.15, .29, .63, motor, 16)
        for angle in np.linspace(0, math.tau, 12, endpoint=False):
            direction = np.array([math.cos(angle), math.sin(angle), 0.])
            g.beam(base+direction*.287+UP*1.91,
                   base+direction*.287+UP*2.39, .032, motor)
        g.cylinder(base+UP*2.50, .315, .13, steel, 16)
        g.cylinder(base+UP*2.575, .235, .028, dark, 16)
        g.box(base-normal*.32+UP*2.17, [.21, .17, .29], motor, [tangent, normal, UP])
        # A conduit ends at the motor terminal enclosure.
        conduit = [base-normal*.38+UP*.12, base-normal*.38+UP*2.14,
                   base-normal*.32+UP*2.14]
        g.tube(conduit, [.022]*3, dark, 6)
        for x in (-.24, .24):
            for y in (-.24, .24):
                g.cylinder(base+tangent*x+normal*y+UP*.225, .034, .05, copper, 6)
        counts['multistagePumps'] += 1
        return {'id': identifier, 'base': base.tolist(), 'position': (base+UP*1.25).tolist(),
                'height': 2.59, 'stageBands': 10,
                'inlet': (base-normal*.31+UP*.36).tolist(),
                'outlet': (base+normal*.31+UP*1.69).tolist()}

    def brace(identifier, a, b, width=.14):
        g.beam(a, b, width, steel)
        supports.append({'id': identifier, 'start': np.asarray(a).tolist(),
                         'end': np.asarray(b).tolist(), 'width': width})

    def skid(identifier, center, normal, tangent, z, width=3.8, depth=2.8):
        center = np.asarray(center)
        g.box(center-UP*.16, [width, depth, .32], dark, [tangent, normal, UP])
        g.box(center+UP*.025, [width, depth, .05], steel, [tangent, normal, UP])
        for x in np.linspace(-width*.45, width*.45, 11):
            # Spaced hatch lines make the compact plinth read as steel grating.
            g.box(center+tangent*x+UP*.055, [.035, depth*.94, .015], dark,
                  [tangent, normal, UP])
        for side in (-1, 1):
            tip = center+tangent*(side*(width/2-.24))+normal*(depth/2-.20)-UP*.27
            root = center-normal*(depth/2+1.15)+tangent*(side*(width/2-.24))-UP*1.9
            brace(identifier+'_Knee_'+str(side), root, tip, .20)
            brace(identifier+'_Bearer_'+str(side), root+UP*1.64, tip, .17)
        counts['supportedStations'] += 1

    try:
        # Existing ground bank: front service row, outside the G0 walk and lift.
        g.group = 'Infrastructure/Boosters/Ground'
        normal = np.array([0., -1., 0.]); tangent = np.array([1., 0., 0.])
        base = np.array([-20.68, -19.69, .12])
        g.box(base-UP*.015, [2.72, 1.12, .24], steel)
        pumps = [pump('GroundPump'+str(i+1), base+tangent*x, normal, tangent)
                 for i, x in enumerate((-.65, .65))]
        supply = np.array([-22.35, -18.65, .48])
        inlet_header = base-normal*.40+UP*.36
        tube('GroundReceiverToHeader', [supply, [-22.35, inlet_header[1], .48], inlet_header])
        outlet_header = base+normal*.42+UP*1.69
        for i, p in enumerate(pumps):
            inlet, outlet = np.array(p['inlet']), np.array(p['outlet'])
            tube('GroundPump%d_Inlet' % (i+1), [inlet_header, [inlet[0], inlet_header[1], inlet[2]], inlet], .105)
            tube('GroundPump%d_Outlet' % (i+1), [outlet, outlet+UP*.45, [outlet[0], outlet_header[1], outlet[2]+.45], outlet_header+UP*.45], .105)
            check_valve('GroundCheck'+str(i+1), outlet+UP*.26, normal, tangent)
        discharge = outlet_header+UP*.45
        tie = np.asarray(ground['points'][1], dtype=float)
        tube('GroundBoosterToExistingSupply', [discharge, [-22.96, discharge[1], discharge[2]],
               [-22.96, tie[1], discharge[2]], [-22.96, tie[1], tie[2]], tie], .14)
        isolation('GroundIsolation', [-22.96, tie[1], 1.87], normal, tangent)
        gauge(discharge+UP*.32, normal, tangent)
        for y in (-19.6, -16.7, -14.05):
            brace('GroundDischargeStand', [-22.96, y, -.20], [-22.96, y, discharge[2]-.13], .09)
        # Mounted zone plate; no unsupported floating markers or pressure numbers.
        g.box([-19.36, -19.79, 1.0], [.23, .12, 1.32], dark)
        g.beam([-19.36, -19.79, .12], [-19.36, -19.79, .52], .075, steel)
        for i, col in enumerate((water, amber, copper)):
            g.box([-19.36, -19.86, .82+i*.26], [.10, .045, .15], col)
        stations.append({'id': 'GroundTwinMultistage', 'deckZ': 0.,
                         'position': base.tolist(), 'pumps': pumps,
                         'footprint': {'min': [-23.20, -20.27, -.24],
                                       'max': [-19.26, -17.3, 2.79]},
                         'receiverConnection': supply.tolist(),
                         'dischargeConnection': tie.tolist(),
                         'serviceArea': 'Existing ground utility reservation; no public floor'})

        for index, z in enumerate(BOOSTER_Z):
            identifier = 'BoosterZone'+str(index+2)
            g.group = 'Infrastructure/Boosters/'+identifier
            anchor = route_at_height(riser, z)
            normal = anchor* [1., 1., 0.]; normal /= np.linalg.norm(normal)
            tangent = np.array([-normal[1], normal[0], 0.])
            center = anchor+normal*1.62
            skid(identifier, center, normal, tangent, z)
            pumps = [pump(identifier+'_Pump'+str(i+1), center+tangent*x+UP*.08, normal, tangent)
                     for i, x in enumerate((-.82, .82))]
            incoming = route_at_height(riser, z+.44)
            outgoing = route_at_height(riser, z+2.33)
            intake = center-normal*.49+UP*.44
            discharge = center+normal*.56+UP*2.33
            tube(identifier+'_RiserIntake', [incoming, intake], .13)
            tube(identifier+'_RiserDischarge', [discharge, discharge+tangent*1.62,
                    outgoing+tangent*1.62, outgoing], .13)
            for i, p in enumerate(pumps):
                inlet, outlet = np.array(p['inlet']), np.array(p['outlet'])
                tube(identifier+'_Pump%d_Intake' % (i+1), [intake, inlet-normal*.18, inlet], .105)
                tube(identifier+'_Pump%d_Discharge' % (i+1), [outlet, outlet+UP*.56,
                     discharge+tangent*((i*2-1)*.82), discharge], .105)
                check_valve(identifier+'_Check'+str(i+1), outlet+UP*.29, normal, tangent)
            isolation(identifier+'_BypassIsolation', route_at_height(riser, z+1.38), normal, tangent)
            gauge(discharge+UP*.28, normal, tangent)
            # Guarded equipment edge, not a new accessible deck or path collider.
            for side in (-1, 1):
                p = center+tangent*(side*1.77)+normal*1.26
                g.beam(p, p+UP*1.04, .052, steel)
            g.beam(center-tangent*1.77+normal*1.26+UP*1.04,
                   center+tangent*1.77+normal*1.26+UP*1.04, .052, steel)
            marker = center-tangent*1.87-normal*.61
            g.box(marker+UP*.65, [.065, .46, 1.12], dark, [tangent, normal, UP])
            g.beam(marker+UP*.06, marker+UP*.26, .075, steel)
            for h in (.3, .62, .94):
                g.box(center-tangent*1.87-normal*.61+UP*h, [.09, .39, .18],
                      amber if index == 0 else copper, [tangent, normal, UP])
            stations.append({'id': identifier, 'deckZ': z, 'position': center.tolist(),
                             'pumps': pumps, 'riserIntake': incoming.tolist(),
                             'riserDischarge': outgoing.tolist(),
                             'support': 'Twin tree-anchored triangular knee braces and bearers',
                             'publicWalkable': False, 'maximumRadialExtent': float(np.linalg.norm(center[:2])+2.4)})

        # Upper water storage is southwest of the trunk, well inside the ring.
        g.group = 'Infrastructure/Boosters/UpperStorage'
        top = np.asarray(riser['points'][-1], dtype=float)
        normal = top*[1., 1., 0.]; normal /= np.linalg.norm(normal)
        tangent = np.array([-normal[1], normal[0], 0.])
        deck = top+normal*1.85+UP*(TANK_DECK_Z-top[2])
        skid('UpperStorage', deck, normal, tangent, TANK_DECK_Z, width=3.5, depth=3.0)
        tank = deck+UP*2.05
        g.cylinder(tank, 1.12, 3.35, steel, 24)
        g.sphere(tank+UP*1.675, [1.12, 1.12, .27], water, 24, 6)
        g.sphere(tank-UP*1.675, [1.12, 1.12, .27], water, 24, 6)
        for height in (-1.27, 1.27):
            g.cylinder(tank+UP*height, 1.151, .11, water, 24)
        for x in (-.68, .68):
            for y in (-.68, .68):
                brace('StorageLeg', deck+tangent*x+normal*y+UP*.10,
                       deck+tangent*x+normal*y+UP*.79, .11)
        fill = tank-normal*.95+UP*1.60
        fill_riser = top+tangent*1.55
        tube('UpperRiserToStorage', [top, fill_riser,
                  [fill_riser[0], fill_riser[1], fill[2]], fill], .13)
        check_valve('StorageFillCheck', top+tangent*1.55+UP*1.06, normal, tangent)
        # Low outlet returns to the existing upper distribution endpoint.
        outlet = tank+normal*1.0-UP*1.22
        tube('StorageReturnToUpperDistribution', [outlet,
                outlet+tangent*1.54,
                [outlet[0]+tangent[0]*1.54, outlet[1]+tangent[1]*1.54, top[2]],
                top+tangent*1.54, top], .13)
        isolation('StorageOutletIsolation', outlet+tangent*1.54-UP*.36, normal, tangent)
        gauge(outlet+normal*.17+UP*.38, normal, tangent)
        # Sight tube plus an overflow terminating at a contained drain tray.
        sight = tank+normal*1.155
        tube('StorageSightTube', [sight-UP*1.20, sight+UP*1.20], .035, water, False, 8)
        for h in (-1.2, 1.2):
            g.beam(sight+UP*h, tank+normal*1.04+UP*h, .05, copper)
        overflow_start = tank-tangent*1.02+UP*1.60
        tray = deck-tangent*1.40+normal*.84+UP*.15
        tube('StorageOverflowToTray', [overflow_start, overflow_start-tangent*.28,
                tray+UP*.18], .063)
        g.box(tray, [.47, .47, .10], dark, [tangent, normal, UP])
        g.cylinder(tank+UP*1.96, .29, .075, dark, 16)
        g.beam(tank+UP*2.02-tangent*.15, tank+UP*2.02+tangent*.15, .035, steel)
        storage = {'id': 'UpperStorage', 'deckZ': TANK_DECK_Z,
                   'position': tank.tolist(), 'radius': 1.151, 'bodyHeight': 3.35,
                   'riserConnection': top.tolist(), 'fillConnection': fill.tolist(),
                   'outletConnection': outlet.tolist(), 'publicWalkable': False,
                   'maximumRadialExtent': float(np.linalg.norm(deck[:2])+2.35)}
    finally:
        g.group = old_group

    added = {key: batch for key, batch in g.batches.items() if key not in keys_before}
    triangle_count = sum(len(b['f']) for b in g.batches.values())-triangles_before
    vertices = np.concatenate([np.asarray(b['v'], dtype=float) for b in added.values()])
    if triangle_count >= TRIANGLE_BUDGET:
        raise ValueError('Booster triangle budget exceeded: '+str(triangle_count))
    if not np.isfinite(vertices).all():
        raise ValueError('Booster geometry contains a non-finite vertex')
    counts.update(triangles=int(triangle_count), batches=len(added),
                  newMaterials=len(set(g.materials)-materials_before),
                  newTextures=0, collisionTriangles=0, runtimeScripts=0)
    return {'enabled': True, 'sourceCoordinates': 'XYZ, Z up, metres',
            'stations': stations, 'storage': storage, 'utilityRoutes': routes,
            'valves': valves, 'supports': supports, 'stats': counts,
            'pressureZones': [
                {'id': 'Zone1', 'fromZ': 0., 'toZ': 52., 'equipment': 'GroundTwinMultistage'},
                {'id': 'Zone2', 'fromZ': 52., 'toZ': 102., 'equipment': 'BoosterZone2'},
                {'id': 'Zone3', 'fromZ': 102., 'toZ': 155., 'equipment': 'BoosterZone3'}],
            'bounds': {'min': vertices.min(axis=0).tolist(), 'max': vertices.max(axis=0).tolist()},
            'collisionAuthored': False, 'engineeringCertified': False,
            'notes': ['Fictional visual environment equipment; not an engineering specification or certified installation.',
                      'Three staged lift zones are indicated visually; no real pressure, flow, capacity or potable-water claim.',
                      'Existing trunk line remains visible as an isolation-valved bypass at each booster skid.',
                      'Ground equipment remains within the existing service bank; riser stands and storage sit outside public walking lanes.',
                      'Pump flanges, check arrows, motor fins, tie rods, gauges and zone bands use geometry and solid materials only.']}


def self_test():
    """Generate only this module plus existing utilities; never the main world."""
    from world_geometry import Geometry
    from tree_infrastructure import add_infrastructure
    from altitude_profile import apply_altitude_profile
    from shapely.geometry import Point, Polygon, LineString, box
    from shapely.ops import unary_union
    from pathlib import Path
    import json
    g = Geometry()
    M = {k: g.material(k, [.4, .4, .4]) for k in ('wood', 'dark', 'iron', 'trim', 'stone', 'ceramic')}
    infra = add_infrastructure(g, M, np.random.default_rng(42))
    apply_altitude_profile(g, None, {'infrastructure': infra})
    legacy = {r['id']: np.array(r['points']) for r in infra['utilityRoutes']}
    spec = add_booster_pumps(g, M, infra)
    checks = {'triangle_budget': spec['stats']['triangles'] < TRIANGLE_BUDGET,
              'six_multistage_pumps': spec['stats']['multistagePumps'] == 6,
              'sixty_stage_bands': spec['stats']['impellerStackBands'] == 60,
              'supported_boosters_and_storage': spec['stats']['supportedStations'] == 3,
              'booster_altitudes': [s['deckZ'] for s in spec['stations']] == [0., 52., 102.],
              'storage_altitude': spec['storage']['deckZ'] == 155.,
              'no_new_textures_or_collision': spec['stats']['newTextures'] == spec['stats']['collisionTriangles'] == 0,
              'existing_routes_unchanged': all(np.array_equal(r['points'], legacy[r['id']]) for r in infra['utilityRoutes'])}
    routes = {r['id']: r for r in spec['utilityRoutes']}
    checks['ground_discharge_connected'] = np.allclose(routes['GroundBoosterToExistingSupply']['points'][-1], legacy['Ground_water'][1])
    checks['upper_supply_connected'] = np.allclose(routes['UpperRiserToStorage']['points'][0], legacy['Trunk_water'][-1]) and np.allclose(routes['StorageReturnToUpperDistribution']['points'][-1], legacy['Trunk_water'][-1])
    # Valve centers must lie on an actual new or retained pipe centerline.
    segments = []
    for route in [*spec['utilityRoutes'], *infra['utilityRoutes']]:
        points = np.asarray(route['points'], dtype=float)
        segments.extend(zip(points[:-1], points[1:]))
    def nearest_pipe(position):
        p = np.asarray(position, dtype=float)
        distances = []
        for a, b in segments:
            d = b-a
            t = np.clip(np.dot(p-a, d)/max(np.dot(d, d), 1e-12), 0., 1.)
            distances.append(np.linalg.norm(p-a-t*d))
        return min(distances)
    checks['all_valves_on_pipe_centerlines'] = all(nearest_pipe(v['position']) < 1e-6 for v in spec['valves'])
    checks['booster_endpoints_on_riser'] = all(np.allclose(routes[s['id']+'_RiserIntake']['points'][0], route_at_height({'points': legacy['Trunk_water']}, s['deckZ']+.44)) and np.allclose(routes[s['id']+'_RiserDischarge']['points'][-1], route_at_height({'points': legacy['Trunk_water']}, s['deckZ']+2.33)) for s in spec['stations'][1:])
    selected = [b for (group, _), b in g.batches.items() if group.startswith('Infrastructure/Boosters/')]
    checks['finite_geometry_and_uvs'] = all(np.isfinite(np.asarray(b[k])).all() for b in selected for k in ('v', 'uv'))
    checks['nondegenerate_faces'] = all(np.min(np.linalg.norm(np.cross(np.asarray(b['v'])[np.asarray(b['f'])][:, 1]-np.asarray(b['v'])[np.asarray(b['f'])][:, 0], np.asarray(b['v'])[np.asarray(b['f'])][:, 2]-np.asarray(b['v'])[np.asarray(b['f'])][:, 0]), axis=1)) > 1e-12 for b in selected)
    # At these elevations the independent staircase is forty metres from trunk.
    checks['lower_stair_radial_clearance'] = all(s['maximumRadialExtent'] < 30 for s in spec['stations'][1:])
    # Validate high storage XY against actual nearby public footprint shapes.
    layout = json.loads((Path(__file__).with_name('layout.reference.json')).read_text())
    nearby = []
    for p in layout['platforms']:
        nearby.append(box(p['x']-p['width']/2, p['y']-p['depth']/2,
                          p['x']+p['width']/2, p['y']+p['depth']/2))
    nearby.append(Point(0, 0).buffer(19.5).difference(Point(0, 0).buffer(16.5)))
    for p in layout['paths']:
        nearby.append(LineString(p['points']).buffer(p['width']/2+.1))
    storage_xy = Point(spec['storage']['position'][:2]).buffer(2.35)
    checks['storage_clear_of_existing_lanes'] = not storage_xy.intersects(unary_union(nearby))
    return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
            'stats': spec['stats'], 'storage': spec['storage'], 'bounds': spec['bounds']}


if __name__ == '__main__':
    import json
    result = self_test()
    print(json.dumps(result, indent=2))
    raise SystemExit(result['status'] != 'PASS')
