"""Open-sided Noh-inspired stage; visual geometry and explicit integration metadata.

Coordinates are metres, X east / Y north / Z up. This module never authors
collision or edits layout data. Call before Geometry.compact().
"""
import math
import numpy as np

STAGE_RADIUS = 14.3
STAGE_ANGLE_DEG = 45.0
STAGE_LEVEL = "L2"
STAGE_Z = 40.0


def stage_layout():
    """Return JSON-safe stage/deck shapes before the main floors are generated."""
    a = math.radians(STAGE_ANGLE_DEG)
    outward = np.array([math.cos(a), math.sin(a), 0.0])
    right = np.array([outward[1], -outward[0], 0.0])
    center = outward * STAGE_RADIUS + [0, 0, STAGE_Z]

    def polygon(xhalf, y0, y1):
        return [(center + right*x + outward*y)[:2].tolist()
                for x, y in [(-xhalf, y0), (xhalf, y0),
                             (xhalf, y1), (-xhalf, y1)]]

    floor = polygon(2.1, -2.1, 2.1)
    deck = polygon(3.15, -2.7, 3.25)
    posts = []
    for x in [-1.84, 1.84]:
        for y in [-1.84, 1.84]:
            posts.append({"name": "NohStage_Post_%s_%s" % (int(x > 0), int(y > 0)),
                          "center": (center + right*x + outward*y + [0, 0, 1.43]).tolist(),
                          "size": [.23, .23, 2.86],
                          "axes": np.array([right, outward, [0, 0, 1]]).reshape(-1).tolist()})
    return {
        "id": "NohStage", "level": STAGE_LEVEL, "z": STAGE_Z,
        "center": center.tolist(), "front": outward.tolist(),
        "right": right.tolist(), "floorPolygon": floor,
        "deckUnionPolygon": deck,
        "floorRecommendation": {"level": STAGE_LEVEL, "z": STAGE_Z,
                                "polygon": deck, "operation": "union_before_floor_and_guard_generation"},
        "solidBoxes": posts,
        "floorTests": [{"id": "NohStage", "position": (center + right*x + outward*y).tolist()}
                       for x, y in [(0, 0), (-1.4, 0), (1.4, 0), (0, -1.4), (0, 2.8)]],
        "floorTopVisualOffset": .012,
        "minimumClearHeight": 2.62,
        "collisionAuthored": False,
        "notes": ["Union deckUnionPolygon into L2 before drawing floors and boundary guards.",
                  "Keep the continuous L2 collider at Z40; the 12 mm cypress finish is cosmetic.",
                  "Four post boxes are recommendations only; caller owns all collision.",
                  "No eye-level back panel or new steps: all four sides remain open.",
                  "Existing ring clear lane from radius 16.5 to 19.5 remains unobstructed."]}


def add_noh_stage(g, M, rng):
    """Add a four-post cypress stage with a hip roof and return its metadata.

    ``rng`` is accepted for the same integration contract as other visual
    modules; deliberate architectural details remain seed-independent.
    """
    del rng
    spec = stage_layout()
    origin = np.array(spec["center"])
    right = np.array(spec["right"])
    outward = np.array(spec["front"])
    axes = [right, outward, [0, 0, 1]]
    old_group = g.group
    start_triangles = sum(len(b["f"]) for b in g.batches.values())
    start_batches = len(g.batches)
    reference = dict(g.materials.get(M.get("counter", M["wood"]), {}))
    for key in ["name", "color", "emission", "roughness"]:
        reference.pop(key, None)
    cypress = g.material("StageCypress", [.98, .87, .66], emission=0,
                         roughness=.82, **reference)
    wood, dark, tile = M["wood"], M["dark"], M["tile"]
    metal = M["trim"]

    def P(x, y, z):
        return origin + right*x + outward*y + [0, 0, z]

    def B(x, y, z, w, d, h, material):
        g.box(P(x, y, z), [w, d, h], material, axes)

    try:
        g.group = "Stage/Noh/Floor"
        # A thin raised finish over the caller's continuous Z40 deck, not a step.
        B(0, 0, -.145, 4.2, 4.2, .29, dark)
        for j in range(14):
            x = -2.1 + (j+.5)*.3
            B(x, 0, .006, .295, 4.18, .012, cypress)
            for y in [-1.96, 1.96]:
                g.cylinder(P(x, y, .013), .007, .003, metal, 6)
        for side in [-1, 1]:
            B(side*2.09, 0, -.075, .075, 4.27, .17, cypress)
            B(0, side*2.09, -.075, 4.27, .075, .17, cypress)
        # Joists and radial knee-braces give the new sector a readable load path.
        g.group = "Stage/Noh/Support"
        for x in [-2.45, 0, 2.45]:
            g.beam(P(x, -2.7, -.49), P(x, 3.25, -.49), .22, dark, .32)
            g.beam(P(x*.5, -5.2, -3.35), P(x, 1.5, -.5), .23, wood)
        for y in [-2.3, 1.9]:
            g.beam(P(-3.05, y, -.62), P(3.05, y, -.62), .26, dark)

        g.group = "Stage/Noh/Posts"
        for x in [-1.84, 1.84]:
            for y in [-1.84, 1.84]:
                B(x, y, 1.43, .23, .23, 2.86, cypress)
                B(x, y, .13, .255, .255, .18, metal)
                B(x, y, 2.72, .38, .38, .14, cypress)
                B(x, y, 2.84, .46, .46, .11, cypress)
                # Compact brackets above head height, no diagonal at eye level.
                for s in [-1, 1]:
                    g.beam(P(x, y, 2.68), P(x+s*.48, y, 2.91), .085, cypress)
                    g.beam(P(x, y, 2.68), P(x, y+s*.48, 2.91), .085, cypress)
        for side in [-1, 1]:
            B(0, side*1.84, 2.78, 4.43, .21, .24, cypress)
            B(side*1.84, 0, 2.78, .21, 4.43, .24, cypress)

        g.group = "Stage/Noh/HipRoof"
        # True hipped roof: the two ends slope to the ridge, with no gable walls.
        z_eave, z_ridge = 2.99, 4.17
        q = [(-2.9, -2.85, z_eave), (2.9, -2.85, z_eave),
             (2.9, 2.85, z_eave), (-2.9, 2.85, z_eave),
             (-1.45, 0, z_ridge), (1.45, 0, z_ridge)]
        v = [P(*p) for p in q]
        faces = [[0, 1, 5], [0, 5, 4], [1, 2, 5],
                 [2, 3, 4], [2, 4, 5], [3, 0, 4]]
        g.add(v, faces, tile, [(p[0], p[1]) for p in q])
        # Interior soffit is independently wound so the open pavilion looks complete.
        g.add([p-[0, 0, .095] for p in v], [f[::-1] for f in faces],
              dark, [(p[0], p[1]) for p in q])
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            g.quad([v[a], v[b], v[b]-[0, 0, .095], v[a]-[0, 0, .095]], dark)
            g.beam(v[a]-[0, 0, .105], v[b]-[0, 0, .105], .13, cypress, .17)
        for a, b in [(0, 4), (3, 4), (1, 5), (2, 5), (4, 5)]:
            g.tube([v[a]+[0, 0, .02], v[b]+[0, 0, .02]], [.075, .075], tile, 8)
        for side in [-1, 1]:
            for x in np.arange(-2.55, 2.56, .43):
                inner_x = float(np.clip(x, -1.42, 1.42))
                g.beam(P(inner_x, 0, z_ridge-.18),
                       P(x, side*2.77, z_eave-.14), .055, cypress, .095)
            # Six modest tile courses read as layered roofing without dense tiles.
            for t in np.linspace(.18, .96, 6):
                half_width = 1.45 + (2.9-1.45)*t
                y, z = side*2.85*t, z_ridge+(z_eave-z_ridge)*t+.012
                g.beam(P(-half_width, y, z), P(half_width, y, z), .029, tile, .047)

        # Pine silhouette only in the high rear transom; no opaque back wall.
        g.group = "Stage/Noh/PineCrest"
        B(0, -1.91, 2.80, 1.12, .055, .23, dark)
        g.beam(P(-.15, -1.947, 2.71), P(.08, -1.947, 2.88), .032, metal)
        for x, z, width in [(-.16, 2.77, .29), (.03, 2.84, .33), (.21, 2.86, .22)]:
            g.beam(P(x-width, -1.955, z), P(x+width, -1.955, z+.012), .028, metal)
            for shift in [-.7, 0, .7]:
                g.beam(P(x+shift*width, -1.955, z),
                       P(x+shift*width+.035, -1.955, z+.045), .017, metal)
    finally:
        g.group = old_group
    stage_vertices = [np.asarray(b["v"]) for (group, _), b in g.batches.items()
                      if group.startswith("Stage/Noh/")]
    vertices = np.concatenate(stage_vertices)
    spec["visualBounds"] = {"min": vertices.min(axis=0).tolist(),
                             "max": vertices.max(axis=0).tolist()}
    spec["stats"] = {"triangles": sum(len(b["f"]) for b in g.batches.values())-start_triangles,
                       "batches": len(g.batches)-start_batches, "posts": 4,
                       "opaqueEyeLevelWalls": 0}
    return spec
