"""Visible utility routes, supported path lamps, telecom and warning lenses.

Visual-only authoring; runtime flashing and all collision belong to the caller.
All returned positions use metres, X east / Y north / Z up.
"""
import json
import math
from pathlib import Path
import numpy as np

TAU = math.tau


def _trunk_frame(z, angle=228.0):
    a = math.radians(angle)
    normal = np.array([math.cos(a), math.sin(a), 0.0])
    tangent = np.array([normal[1], -normal[0], 0.0])
    center = np.array([.9*math.sin(z*.075), 1.5*math.sin(z*.047), z])
    radius = np.interp(z, [-1, 0, 20, 40, 60, 85, 108, 119],
                       [13.8, 13, 9.6, 8, 6.4, 3.8, 1.7, .15])
    # The procedural bark can protrude by about 8%; offset utility rails beyond it.
    return center + normal*(radius*1.10+.42), normal, tangent, center, radius


def _rounded_route(points, bend=.24):
    """Small sampled elbow bends instead of implausible sharp tube corners."""
    points = np.asarray(points, dtype=float)
    out = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:]):
        before, after = a-b, c-b
        lb, la = np.linalg.norm(before), np.linalg.norm(after)
        radius = min(bend, lb*.23, la*.23)
        q0, q1 = b+before/lb*radius, b+after/la*radius
        out.append(q0)
        for t in [.25, .5, .75, 1.0]:
            out.append((1-t)**2*q0+2*(1-t)*t*b+t*t*q1)
    out.append(points[-1])
    return out


def add_infrastructure(g, M, rng, layout=None):
    """Return beacons, practical light specs and explicit visual integration data.

    A warning lens is the only mesh in its own group. The Beacon shader supplies
    a timed pulse; never bake its red emission into surrounding surfaces.
    Pass the caller's working layout when routes or stairs have been changed.
    """
    del rng
    if layout is None:
        layout = json.loads((Path(__file__).with_name("layout.reference.json")).read_text())
    old_group = g.group
    start_triangles = sum(len(b["f"]) for b in g.batches.values())
    start_batches = len(g.batches)
    steel = g.material("UtilityGalvanized", [.40, .46, .47], roughness=.49, metallic=.78)
    copper = g.material("UtilityCopper", [.57, .29, .125], roughness=.42, metallic=.83)
    water = g.material("UtilityWaterBlue", [.075, .28, .34], roughness=.62, metallic=.48)
    gas = g.material("UtilityGasOchre", [.65, .43, .075], roughness=.61, metallic=.40)
    rubber = g.material("UtilityCable", [.025, .03, .029], roughness=.85)
    red = g.material("AviationRed", [1.0, .016, .006], emission=4.5, roughness=.24, shader="Beacon")
    red_off = g.material("AviationRedHousing", [.22, .009, .005], roughness=.31)
    lamp_glow = g.material("UtilityLampWarm", [1.0, .66, .27], emission=1.8, roughness=.48)
    iron, wood, dark = M["iron"], M["wood"], M["dark"]
    lights, beacons, routes, pole_bases = [], [], [], []
    counts = {"pipeClamps": 0, "pathPoles": 0, "junctionBoxes": 0,
              "telecomPanels": 0, "warningBeacons": 0}

    def tube(points, r, material, segments=8, rounded=False):
        p = _rounded_route(points) if rounded else points
        g.tube(p, [r]*len(p), material, segments)

    def collar(p, r, normal, tangent):
        # A short cylindrical band shares the vertical route axis at each clamp.
        g.cylinder(p, r+.025, .09, steel, 8)
        g.beam(p-normal*.05, p-normal*.35, .052, steel)
        counts["pipeClamps"] += 1

    def box_with_door(p, size, normal, tangent, name="junction"):
        p = np.asarray(p)
        g.box(p, size, steel, [tangent, normal, [0, 0, 1]])
        front = p+normal*(size[1]/2+.015)
        g.box(front, [size[0]*.87, .023, size[2]*.87], iron,
              [tangent, normal, [0, 0, 1]])
        g.box(front+tangent*size[0]*.28, [.025, .047, .13], copper,
              [tangent, normal, [0, 0, 1]])
        counts["junctionBoxes"] += 1

    def add_lamp(base, inward, name, height=3.45, feed_inset=.24, feed_depth=.77):
        base = np.asarray(base, dtype=float)
        inward = np.asarray(inward, dtype=float)
        top = base + [0, 0, height]
        arm = top + inward*.42
        g.cylinder(base+[0, 0, .055], .15, .11, steel, 8)
        g.cylinder(base+[0, 0, height*.5], .075, height, dark, 8, r2=.048)
        g.beam(top, arm, .07, steel)
        g.beam(arm, arm-[0, 0, .25], .034, iron)
        center = arm-[0, 0, .4]
        g.box(center, [.26, .26, .30], lamp_glow)
        g.box(center+[0, 0, .185], [.40, .40, .07], dark)
        g.box(center-[0, 0, .18], [.32, .32, .055], iron)
        for dx in [-.145, .145]:
            for dy in [-.145, .145]:
                g.beam(center+[dx, dy, -.16], center+[dx, dy, .16], .025, iron)
        # External post bracket reaches the actual slab edge, below walking level.
        g.beam(base-[0, 0, .22], base+inward*.38-[0, 0, .22], .09, steel)
        tube([base+inward*feed_inset-[0, 0, feed_depth], base-[0, 0, .48],
              base+[0, 0, height-.08], arm-[0, 0, .08]],
             .016, rubber, 6, True)
        pole_bases.append({"name": name, "position": base.tolist(), "radius": .15})
        lights.append({"position": (center-[0, 0, .19]).tolist(), "range": 4.0,
                       "strength": .85, "name": name, "bakedOnly": True})
        counts["pathPoles"] += 1
        return top+[0, 0, .055]

    def suspended_wire(a, b, sag=.12):
        a, b = np.asarray(a), np.asarray(b)
        length = np.linalg.norm(b-a)
        sag = min(sag, length*.025)
        pts = [(1-t)*a+t*b-[0, 0, sag*4*t*(1-t)] for t in np.linspace(0, 1, 7)]
        tube(pts, .017, rubber, 6)

    def beacon(identifier, p, period=2.0, duty=.16, phase=0.0):
        p = np.asarray(p, dtype=float)
        g.group = "Infrastructure/Telecom/BeaconHousing"
        g.cylinder(p-[0, 0, .15], .22, .12, steel, 12)
        g.cylinder(p, .164, .20, red_off, 12)
        for a in np.linspace(0, TAU, 4, endpoint=False):
            dx, dy = .183*math.cos(a), .183*math.sin(a)
            g.beam(p+[dx, dy, -.13], p+[dx, dy, .22], .018, steel)
        g.cylinder(p+[0, 0, .235], .215, .055, steel, 12)
        group = "Infrastructure/WarningBeacons/" + identifier
        g.group = group
        g.sphere(p+[0, 0, .015], [.178, .178, .205], red, 12, 7)
        beacons.append({"id": identifier, "position": (p+[0, 0, .015]).tolist(),
                        "group": group, "material": red,
                        "rendererName": "Mesh_"+group.replace("/", "_")+"_"+red,
                        "hierarchyPath": "Visuals/"+group,
                        "period": period, "dutyCycle": duty, "phase": phase,
                        "animation": "TreeTopYokocho/Beacon shader _Time pulse",
                        "range": 4.0, "strength": 1.4,
                        "color": [1.0, .018, .004], "realtimeShadows": False,
                        "excludeFromLightmap": True})
        counts["warningBeacons"] += 1

    try:
        # Separate water, gas and electrical risers remain legible for 90 metres.
        g.group = "Infrastructure/Trunk/Risers"
        zs = np.unique(np.r_[np.arange(1.3, 94.01, 2.7), [34., 40., 46., 52., 78., 94.]])
        service = [("water", -.48, .11, water, 52.),
                   ("gas", -.12, .068, gas, 46.),
                   ("electrical", .28, .12, steel, 94.),
                   ("telecom", .61, .049, rubber, 94.)]
        for name, offset, radius, material, top_z in service:
            heights = sorted(set([float(z) for z in zs if z < top_z]+[top_z]))
            points = [_trunk_frame(z)[0]+_trunk_frame(z)[2]*offset for z in heights]
            tube(points, radius, material, 10 if name == "water" else 8)
            routes.append({"id": "Trunk_"+name, "kind": name,
                           "points": [p.tolist() for p in points], "radius": radius})
            for z in np.arange(2.0, top_z-.2, 3.4):
                anchor, normal, tangent, _, _ = _trunk_frame(z)
                collar(anchor+tangent*offset, radius, normal, tangent)
        g.group = "Infrastructure/Trunk/Brackets"
        for z in np.arange(2, 94, 3.4):
            p, normal, tangent, center, radius = _trunk_frame(z)
            g.beam(p-tangent*.77, p+tangent*.82, .065, steel)
            for side in [-1, 1]:
                g.beam(p+tangent*(side*.64),
                       center+normal*(radius*.95)+tangent*(side*.64), .072, steel)
        for z in [3., 33.0, 39.0, 45.0, 51.0, 77.0, 91.5]:
            p, normal, tangent, _, _ = _trunk_frame(z)
            box_with_door(p+tangent*1.10+normal*.07, [.47, .25, .64], normal, tangent)
            tube([p+tangent*.28, p+tangent*.28+[0, 0, .32],
                  p+tangent*1.10+[0, 0, .32]], .052, steel, 8, True)

        # The compact equipment bank is outside the lift approach and existing G0 lanes.
        g.group = "Infrastructure/Ground/ServiceBank"
        g.box([-21.2, -18.8, -.17], [4., 3., .34], M["stone"])
        for x in [-22.75, -19.65]:
            for y in [-20., -17.6]:
                g.box([x, y, -2.2], [.3, .3, 4.1], steel)
        normal, tangent = np.array([0., -1., 0.]), np.array([-1., 0., 0.])
        box_with_door([-20.0, -18.65, .97], [1.10, .80, 1.84], normal, tangent)
        for z in np.arange(.55, 1.6, .13):
            g.box([-20., -19.065, z], [.79, .025, .031], iron)
        # Receiver tank, pump and guarded gas manifold.
        g.cylinder([-22.35, -18.65, .82], .45, 1.50, water, 16)
        g.sphere([-22.35, -18.65, 1.57], [.45, .45, .15], water, 12, 5)
        g.box([-22.35, -19.47, .35], [.62, .55, .55], steel)
        g.cylinder([-21.35, -18.65, .68], .24, 1.19, gas, 12)
        g.cylinder([-21.35, -18.65, 1.29], .19, .10, steel, 12)
        for x in [-21.75, -20.95]:
            g.beam([x, -19.0, .08], [x, -19., 1.56], .05, steel)
        g.beam([-21.75, -19., 1.56], [-20.95, -19., 1.56], .05, steel)
        # Valve hand wheels: low-poly open rings, not solid inaccessible boxes.
        for x, y, z, material in [(-22.35, -19.55, .72, water),
                                   (-21.35, -19., 1.28, gas)]:
            wheel = [[x+.13*math.cos(a), y, z+.13*math.sin(a)]
                     for a in np.linspace(0, TAU, 13)]
            tube(wheel, .018, copper, 6)
            for a in [0, math.pi/2]:
                g.beam([x-.12*math.cos(a), y, z-.12*math.sin(a)],
                       [x+.12*math.cos(a), y, z+.12*math.sin(a)], .015, copper)
        for i, (kind, offset, radius, material, _) in enumerate(service[:3]):
            root, _, t, _, _ = _trunk_frame(1.3)
            origin = [[-22.35, -18.65, 1.3], [-21.35, -18.65, 1.3], [-20., -18.65, 1.3]][i]
            # Non-walkable north side of lift, deliberately no cross-floor cable.
            points = [origin, [origin[0], -14.05+i*.23, 1.3],
                      [-13.5, -14.05+i*.23, 1.3], root+t*offset]
            tube(points, radius*.8, material, 8, True)
            routes.append({"id": "Ground_"+kind, "kind": kind,
                           "points": [np.asarray(p).tolist() for p in points], "radius": radius*.8})
        for x, y in [(-22., -14.), (-17., -14.), (-13.5, -14.)]:
            g.beam([x, y, -4.], [x, y, 1.2], .10, steel)
            g.beam([x, y-.55, 1.17], [x, y+.75, 1.17], .09, steel)

        # Main-ring distribution is below its slab and never across a walking surface.
        g.group = "Infrastructure/Deck/Distribution"
        for kind, radius, z, material, thickness in [
                ("water", 17.12, 39.10, water, .074),
                ("gas", 16.84, 39.08, copper, .048),
                ("electrical", 19.42, 39.23, rubber, .047)]:
            points = [[radius*math.cos(a), radius*math.sin(a), z]
                      for a in np.linspace(0, TAU, 97)]
            tube(points, thickness, material, 8)
            p, normal, tangent, _, _ = _trunk_frame(z)
            p = p+tangent*{"water": -.48, "gas": -.12, "electrical": .28}[kind]
            destination = [radius*normal[0], radius*normal[1], z]
            tube([p, destination], thickness, material, 8)
            for a in np.linspace(0, TAU, 24, endpoint=False):
                x, y = radius*math.cos(a), radius*math.sin(a)
                g.beam([x, y, z], [x, y, 39.65], .037, steel)
            routes.append({"id": "MainRing_"+kind, "kind": kind,
                           "points": points, "radius": thickness})

        # Poles sit outside the outer rim; wires are carried above 3.2 m clearance.
        g.group = "Infrastructure/Lamps/MainRing"
        ring_tops = []
        for i, a in enumerate(np.linspace(0, TAU, 16, endpoint=False)+math.pi/16):
            outward = np.array([math.cos(a), math.sin(a), 0.])
            base = outward*19.66+[0, 0, 40]
            ring_tops.append(add_lamp(base, -outward, "MainRingElectric_%02d" % i))
        for a, b in zip(ring_tops, ring_tops[1:]+ring_tops[:1]):
            suspended_wire(a, b, .15)

        from shapely.geometry import LineString, Point
        stairs = [LineString([s["start"][:2], s["end"][:2]]).buffer(s["width"]/2+.65)
                  for s in layout["stairs"]]
        levels = {level["id"]: level["z"] for level in layout["levels"]}
        for path in layout["paths"]:
            g.group = "Infrastructure/Lamps/"+path["id"]
            level = levels[path["level"]]
            points = np.asarray(path["points"], dtype=float)
            # Segment-local pole pairs make every overhead wire end on a support.
            for segment, (a, b) in enumerate(zip(points, points[1:])):
                direction = (b-a)/np.linalg.norm(b-a)
                side = np.array([direction[1], -direction[0]])
                # Keep the path-edge conduits below floor and mechanically supported.
                off = side*(path["width"]/2+.07)
                line_a, line_b = np.r_[a+off, level-.53], np.r_[b+off, level-.53]
                tube([line_a, line_b], .028, steel, 6)
                for t in np.linspace(0, 1, max(2, int(np.linalg.norm(b-a)/2.7)+1)):
                    p = line_a*(1-t)+line_b*t
                    g.beam(p, p+[0, 0, .23], .031, steel)
                tops = []
                for index, t in enumerate(np.linspace(.06, .94, max(2, math.ceil(np.linalg.norm(b-a)/5.4)+1))):
                    xy = (1-t)*a+t*b+side*(path["width"]/2+.16)
                    # Stair exclusion includes its entry and head-clearance corridor.
                    if any(s.covers(Point(xy)) for s in stairs):
                        continue
                    base = np.r_[xy, level]
                    tops.append(add_lamp(base, np.r_[-side, 0],
                                         "%s_Electric_%d_%d" % (path["id"], segment, index),
                                         feed_inset=.09, feed_depth=.53))
                for p, q in zip(tops, tops[1:]):
                    suspended_wire(p, q)

        # Lift-side cable rails visibly continue power from each landing to its level.
        g.group = "Infrastructure/Lift/Feed"
        for x in [-18.03, -17.85]:
            tube([[x, -16.08, 1.3], [x, -16.08, 47.1]], .040, steel, 8)
            for z in np.arange(2.0, 47.0, 3.0):
                g.beam([x, -16.08, z], [-17.62, -16.38, z], .032, steel)
        for z in [33.4, 39.4, 45.4]:
            p, _, _, _, _ = _trunk_frame(z)
            tube([p, [-18.03, -16.08, z]], .033, rubber, 6)
            box_with_door([-18.03, -16.11, z+1.1], [.34, .20, .46],
                          np.array([-1., 0, 0]), np.array([0., 1., 0]))

        # A braced telecom mast is clamped to the upper tree, with a real cable feed.
        g.group = "Infrastructure/Telecom/Mast"
        mast = np.array([-2.9, -4.7, 0.])
        zs_mast = np.linspace(91.5, 124.0, 8)
        widths = np.linspace(.72, .36, len(zs_mast))
        for i in range(len(zs_mast)-1):
            for xside, yside in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                points = [mast+[xside*widths[index]/2, yside*widths[index]/2, zs_mast[index]]
                          for index in [i, i+1]]
                tube(points, .033, steel, 8)
            for axis in [0, 1]:
                for side in [-1, 1]:
                    lo, hi = mast.copy(), mast.copy()
                    lo[axis] += side*widths[i]/2; hi[axis] += side*widths[i+1]/2
                    lo[1-axis] -= widths[i]/2; hi[1-axis] += widths[i+1]/2
                    lo[2], hi[2] = zs_mast[i], zs_mast[i+1]
                    g.beam(lo, hi, .027, steel)
                    cross = hi.copy(); cross[1-axis] -= widths[i+1]
                    other = lo.copy(); other[1-axis] += widths[i]
                    g.beam(other, cross, .027, steel)
            z, w = zs_mast[i], widths[i]
            corners = [mast+[x*w/2, y*w/2, z] for x, y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
            for p, q in zip(corners, corners[1:]+corners[:1]):
                g.beam(p, q, .037, steel)
        # Two tree saddles and diagonal knees are the tower's visual support.
        for z in [91.7, 99.0, 106.0]:
            trunk, _, _, center, radius = _trunk_frame(z)
            for dy in [-.48, .48]:
                g.beam(center+[0, dy, 0], mast+[0, dy, z], .14, steel)
                g.beam(center+[0, dy, -1.5], mast+[0, dy, z], .09, steel)
        feed, _, tangent, _, _ = _trunk_frame(94.)
        tube([feed+tangent*.61, mast+[.25, 0, 94.], mast+[.19, 0, 121.8]], .024, rubber, 6, True)
        g.group = "Infrastructure/Telecom/Equipment"
        box_with_door(mast+[0, -.25, 92.7], [.95, .48, 1.05],
                      np.array([0., -1, 0]), np.array([-1., 0, 0]))
        for angle in [15., 135., 255.]:
            a = math.radians(angle)
            normal = np.array([math.cos(a), math.sin(a), 0.])
            tangent = np.array([normal[1], -normal[0], 0.])
            center = mast+normal*.70+[0, 0, 119.8]
            for z in [-.58, .58]:
                g.beam(mast+[0, 0, 119.8+z], center+[0, 0, z], .045, steel)
            g.box(center, [.34, .17, 1.75], M["ceramic"], [tangent, normal, [0,0,1]])
            tube([center-[0, 0, .87], center-normal*.2-[0, 0, 1.10],
                  mast+[.15, 0, 118.7]], .018, rubber, 6, True)
            counts["telecomPanels"] += 1
        # A small point-to-point dish, modeled as a shallow bowl of 12 sectors.
        center = mast+[-.95, 0., 113.5]
        normal = np.array([-1., 0., .13]); normal /= np.linalg.norm(normal)
        tangent = np.array([0., 1., 0.]); up = np.cross(normal, tangent)
        vertices = [center-normal*.12]
        for a in np.linspace(0, TAU, 13):
            vertices.append(center+tangent*(.55*math.cos(a))+up*(.55*math.sin(a)))
        g.add(vertices, [[0, i+1, i] for i in range(1, 13)], M["ceramic"])
        g.add([p-normal*.035 for p in vertices], [[0, i, i+1] for i in range(1, 13)], steel)
        g.beam(mast+[0, 0, 113.4], center-normal*.12, .065, steel)
        g.beam(center, center+normal*.45, .035, steel)
        g.sphere(center+normal*.45, [.055]*3, rubber, 8, 5)
        tube([mast+[0, 0, 123.8], mast+[0, 0, 124.8]], .06, steel, 8)
        beacon("Apex", mast+[0, 0, 124.95], phase=0.0)
        g.group = "Infrastructure/Telecom/Mast"
        g.beam(mast+[0, 0, 105.6], mast+[-.70, 0, 105.6], .05, steel)
        beacon("Mid", mast+[-.70, 0, 105.8], phase=0.0)
        g.group = "Infrastructure/Telecom/Mast"
        g.beam(mast+[0, 0, 94.8], mast+[.72, 0, 94.8], .05, steel)
        beacon("Lower", mast+[.72, 0, 95.0], phase=0.0)
    finally:
        g.group = old_group

    counts["triangles"] = sum(len(b["f"]) for b in g.batches.values())-start_triangles
    counts["batches"] = len(g.batches)-start_batches
    return {"beacons": beacons, "lights": lights, "stats": counts,
            "utilityRoutes": routes, "poleBases": pole_bases,
            "collisionAuthored": False,
            "serviceReservation": {"min": [-23.2, -20.3, -4.25], "max": [-19.2, -17.3, 2.0]},
            "notes": ["Treat service pad as a visual equipment plinth, not a public floor.",
                      "All path poles are outboard of the specified path widths; conduits are below decks.",
                      "Warning groups contain emission lenses only. Exclude them from static batching and baked GI.",
                      "Beacon shader uses a shared 2-second _Time clock, 16% duty, soft pulse; Python preview is a static ON pose.",
                      "Use exact rendererName or hierarchyPath from beacons after Unity geometry import.",
                      "No physics surfaces or CPU runtime behaviours are created by this visual module."]}
