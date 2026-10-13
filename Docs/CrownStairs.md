# Continuous ground-to-crown stair route

`Source/crown_stairs.py` adds a physically continuous, reversible walking route from the protected ground court to an observatory at source Z = 112 m. It does not require teleportation. Source coordinates are X east, Y north, Z up. This is a fictional environment asset, not construction-ready structural design.

## Route and geometry

- A 3 m-wide, guarded ground boardwalk leaves G0 at (-26, -29, 0), passes west of the tree, makes a broad northern turn, and meets the stair base near (-6.946, 39.392, 0). It remains at Z = 0; the lower forest/road surface is scenery and is not an exposed walkable step.
- The 2.8 m nominal-width helix initially uses radius 40 m. Its radius smoothly reduces from 40 m at Z = 52 to 20 m at Z = 112. Angle is 100 + 5t degrees. The elevation parameter is locally remapped to form genuine flat landings at Z = 34 and Z = 52, each approximately 3.21 m long.
- The Z = 34 landing has a 3 m-wide radial bridge into the arrival deck at (0, -32, 34).
- The Z = 52 landing connects eastward to radius 44 m, then follows a northern elevated arc and rounded northwest elbow into the existing lookout at (-28, 24, 52). Radius 44 deliberately separates this bridge's 8 m barriers from the continuing upward helix. Radius 41 would intersect that route.
- The Z = 112 observatory is a 6 m-wide annular horseshoe, radius 17–23 m, running counterclockwise from 300° to 605°. The missing 245–300° sector leaves the ascending stair and its sidewalls clear of the deck underside. The walking sample at the closed far end stops at least 0.60 m before the end barrier.
- The visible staircase has 749 treads. Risers are 146–150 mm; going is 261–523 mm. The physical walking surface is a smooth, closed ramp beneath the decorative steps, avoiding hundreds of collision risers. The stair's clear width between the inward faces of the 240 mm barriers is 2.56 m.
- Every exposed side has a closed, slope-following safety prism extending 350 mm below the walking surface and 8 m above it. Visible timber rails and posts are separate from invisible fall protection. Junction barriers are clipped to adjoining floor footprints, leaving attachment openings rather than walls across the route.
- Radial timber brackets, lower ties and observatory support hoops are visible below the deck surfaces. Lantern fixtures follow the route's outer rail, with physically traced, sagging insulated wire between them. All materials reuse the world palette.

## Integration

Import both functions before legacy guard creation:

```python
from crown_stairs import add_crown_stairs, crown_attachment_openings
```

`crown_attachment_openings()` is safe to call before any new geometry exists. It returns three records containing `id`, `level`, `z`, `width`, `centerline` and conservative `bounds`.

For each legacy level, turn its matching centerline XY coordinates into a Shapely `LineString` and buffer it by `width / 2 + 0.10` with flat caps. Remove only the overlapping portions from legacy safety barriers **and visible railings**. Leave legacy floor slabs intact. The relevant openings are:

1. G0 west edge, near (-26, -29, 0)
2. L1 south edge, near (0, -34, 34)
3. L4 west/northwest edge, near (-29.5, 24.9, 52)

The northwest connector ends with the same straight attachment direction described by its corridor record. Its preceding elbow is rounded to prevent inward rails from folding through the centerline. Only cutting the legacy safety collider, while leaving the visible railing across the corridor, is not sufficient.

After scenery and utilities, before compacting geometry or baking lights:

```python
crown = add_crown_stairs(g, c, M, rng)
lights.extend(crown['lights'])
floorTests.extend(crown['floorTests'])
wallTests.extend(crown['wallTests'])
routes.extend(crown['routes'])
```

Include `crown['route']`, `crown['barriers']`, `crown['lampTests']`, `crown['wireRuns']` and `crown['cameras']` in the manifest under suitable new keys. New barrier records intentionally do not use the legacy level-keyed `guards` schema; retain them separately so existing code does not look up non-existent level names.

No legacy mesh is rewritten by this module. The caller owns the three attachment cuts and final whole-world regression tests. The function restores `g.group` and `c.group` when finished. `rng` is accepted for compatibility but not consumed, so adding the route does not perturb later scenery randomness.

## Returned data

- `lights`: world-compatible `position`, `range`, `strength`, plus a stable fixture ID
- `floorTests`: front-facing floor probes, including centerline samples and regular shoulder probes
- `wallTests`: crossing rays at 1 m and 7.5 m above selected sidewall bases, with source group IDs
- `routes`: five authoritative walking paths, containing `name`, `type`, `width`, `points`, `length`, `sampleSpacingMax`, and `reversible`
- `route`: overall connection graph, a continuous `mainAscentSamples` list from G0 through the helix and onto the crown observatory, attachment openings, dimensions, landing definitions and statistics
- `barriers`: every closed prism's endpoints, footprint, base offset, height, thickness and collision group
- `lampTests`: fixture identity, base, light position and cable-height metadata
- `wireRuns`: the actual sampled wire centerlines, not approximate unconnected decoration
- `cameras`: complete-ascent, arrival, northern-bridge and observatory framing suggestions
- `stats`: added geometry and fixture counts

Every authoritative route segment is at most 0.44 m long. The complete ascent is ordered and connected; reverse its samples to test descent. The two bridges are branches off the ascent, not substitutes for part of it.

Physical slabs use `Floors/Crown…` or `Ramps/Crown…` groups. Invisible walls use `Safety/Crown/…`. Materials are batched by route and 8 m height band. Adjacent ramp bands share their exact cross-section offsets, preventing hairline cracks at band boundaries. Each slab batch is closed; each safety primitive has 8 corners and exactly 12 consecutive outward triangles, making independent solid slicing straightforward. Do not interpret an entire ring of barrier prisms as a filled polygon.

## Standalone verification

Tested with the project's Python environment, using only this module and `Geometry`; the main world generator was not run by the module author.

- 2,457 downward, front-facing floor probes: passed, including exact 8 m band seams and shoulders
- 2,026 front-facing barrier crossing rays: passed
- Every closed floor/ramp batch and every individual 12-triangle barrier prism: watertight, finite and consistently outward wound
- All five route centerlines tested against the sidewall primitives with a 0.25 m horizontal avatar radius and standing body height: zero blocked samples
- Upward floor-collider headroom tests over the new routes: no slab within 2.2 m of the walking surface
- Decorative tread dimensions: all rises at most 150 mm and all going at least 261 mm
- Authoritative route sample separation: at most 0.44 m
- 95,052 visual triangles + 64,904 collision triangles = **159,956 added triangles**
- 109 lantern fixtures, 105 connected wire runs, 4,036 closed safety prisms

These are offline geometric checks, not Unity/VRChat runtime validation. Final whole-world checks must also include original floor, barrier and shop colliders after attachment cuts, plus visual inspection for branch/foliage overlap. The continuous route's collider layout is kept outside the original shop footprints; tree and foliage visual geometry may still require sightline pruning by the scenery stage.

## Independent integrated-world regression

After regeneration, run:

```bash
python Source/validate_crown.py
```

An optional first argument selects another project root. The verifier reads the final `WorldManifest.json` (including the complete `crownStairs` return value), actual `CollisionMeshes.bytes`, and all manifest `solidBoxes`. It never imports the authoring module or runs the generator. Results are written to `Docs/crown_validation.json`, and the process exits nonzero for failure or missing integrated metadata.

Coverage includes all five authoritative routes, their join coordinates, ground-to-Z112 continuity, attachment footprints on the original G0/L1/L4 slabs, exact-height front-facing floor probes, eight radial support probes, and continuous capsule-footprint sweeps subdivided to at most 0.20 m. Sweeps test the entire integrated world, including original safety walls and oriented shop/utility `solidBoxes`, for 0.25 m radius, 1.65 m standing height and at least 2.2 m overhead clearance. Actual slab triangles are checked for overhead obstructions. All emitted guard rays are tested against the final Safety meshes.

Every 12-triangle safety primitive is clipped separately to the swept body's elevation interval before its XY projection is tested. This avoids the erroneous “filled interior” caused by polygonizing an entire closed perimeter. The standing-body test uses a conservative swept cylinder, not a Unity capsule-controller simulation; the report records this assumption and its slope/support tolerances. A PASS establishes offline geometric coverage only. Unity, Udon and VRChat runtime validation remain separate.
