# Continuous high-canopy crown staircase

`Source/high_crown_stairs.py` is the raised-world replacement for `crown_stairs.py`. It does not modify the original module, reference layout, main generator, or existing meshes. Source coordinates remain XYZ, Z up, in metres.

## Geometry and exact joins

The continuous, reversible walking route starts at G0 **Z0**, reaches the elevated alley arrival at **Z134**, connects to the lookout at **Z152**, and finishes on the crown observatory at **Z212**. No teleport is needed to complete the route.

- Ground attachment: **(-20, -29, 0)**, using the guarded west-side approach
- Arrival attachment inside L1: **(0, -32, 134)**; its helix landing is **(0, -40, 134)**
- Lookout attachment inside L4: **(-28, 24, 152)**; its helix landing is **(40, 0, 152)**
- Crown entry: **(10, -17.3205080757, 212)**

The lower helix adds two complete turns to the old design. It turns from 100° at ground to 990° at the arrival landing, followed by the original upper route translated upward by 100 m. Total winding is **3.5556 turns**. The complete ground approach, ascent and observatory walk is **1,136.80 m** long.

The stair slab is **2.8 m** wide. The 0.24 m thick safety walls are centred on its edges, giving **2.56 m** unobstructed width between their inner faces. Branch bridges and the ground approach are 3 m wide; the observatory is 6 m wide. The L1 flat landing is 3.739 m long and the L4 flat landing is 3.211 m long.

There are **1,416 horizontal visual treads**, with rises of **146.0–149.93 mm** and centreline going of at least **261.31 mm**. The continuous physical ramp under them avoids separate step-collider seams. Its steepest centreline segment is **29.811°**; the steepest actual float32 ramp triangle, including the inner edge, is **31.224°**. Both stay below 32°.

## Integration

Before generating the legacy rails and safety walls, import:

```python
from high_crown_stairs import add_crown_stairs, crown_attachment_openings
```

`crown_attachment_openings()` retains the existing three-record API: `id`, `level`, `z`, `width`, `centerline`, and conservative XY `bounds`. The G0 record stays at Z0; L1 and L4 records are now at Z134 and Z152. Their attachment XY and corridor directions are unchanged.

For each matching legacy level, buffer the record's XY centreline by `width / 2 + 0.10`, using flat caps. Cut that corridor from **both** the existing safety walls and visible rails. Keep the original floor slabs intact. Regenerate the corresponding legacy wall probes so deleted wall segments do not leave stale test rays.

After scenery and utilities, before compacting meshes or baking lights:

```python
crown = add_crown_stairs(g, c, M, rng)
lights.extend(crown['lights'])
floorTests.extend(crown['floorTests'])
wallTests.extend(crown['wallTests'])
routes.extend(crown['routes'])
```

Save the complete returned dictionary as `manifest['crownStairs']`. Existing field names are unchanged. `route.helixTurns` and `route.legacyHeightOffset` provide additional raised-world metadata. Both geometry group settings are restored on return, and the random generator is not consumed.

The main generator must apply its +100 m elevation change to the legacy L1/L2/L3/L4 decks, props, colliders and records before adding this module. Do **not** translate the new staircase again. Do not translate G0. Whole-world validation must expect the requested crown height of 212 m rather than the previous hardcoded 112 m.

## Mesh, safety and visual contracts

- Physical decks use `Floors/Crown…`; the main helix uses `Ramps/Crown…`
- Invisible sidewalls use `Safety/Crown/…`, with **8 m** height above the local walking surface
- Every wall is a separate closed solid with **8 corners and exactly 12 consecutive outward-facing triangles**
- Slabs are closed per 8 m height band; neighbouring bands share the exact cross-section offsets
- Authoritative route samples are no more than **0.44 m** apart
- Walls and rails are clipped at the adjoining route footprints and legacy slab openings
- The crown retains its 55° approach notch, preventing the observatory slab from obstructing the last section of stairs
- The ground approach, arrival bridge, lookout bridge and observatory receive distinct **8, 10, 12 and 14 mm** visual finishes to avoid coplanar opaque surfaces at joins; collision elevations remain exact
- Lanterns, poles and sagging insulated wires follow the outside rail, clear of the walking lane

Bracket roots use the same smooth elevation mapping as the tall tree: original Z≤14 stays fixed; Z14–33 gains `100 * smoothstep((z - 14) / 19)`; Z≥33 gains 100 m. Roots follow the trunk's existing small XY drift and terminate at 60% of its local radius, allowing for bark ridges and ring interpolation. The observatory beams and hoops remain below its slab.

New pumps, towers and service props must be checked against the outer circulation envelope. Below Z152 the helix centreline is at radius 40 m; the north lookout branch reaches radius 44 m at Z152. Keeping only props' centres outside a centreline is insufficient: include their full oriented collision boxes and the avatar radius.

## Reproducible standalone validation

From the project root, using its installed requirements:

```bash
python Source/high_crown_stairs.py --self-test --report /tmp/high_crown_validation.json
```

This builds only the new module, serializes its colliders to the same float32 binary format as the world, reads those actual triangles back, and runs independent ray and Z-clipped solid tests from `validate_crown.py`. Three simple legacy attachment-slab fixtures are included at G0/L1/L4: the final half-avatar beyond each bridge endpoint is supported by its existing deck. These fixtures contain no legacy walls, shops or scenery.

Verified on 2026-10-13:

- **3,969** emitted floor probes passed
- **3,313** route-centre floor probes passed
- **13,248** radial foot-support probes passed
- **7,471** continuous swept segments passed for a 0.25 m avatar radius, 1.65 m standing body and 2.2 m headroom
- **3,286** front-facing guard rays passed
- All **6,556** independent safety prisms and all floor/ramp batches are finite, watertight, consistently wound, positive-volume solids
- Exact ground/helix/bridge/crown joins, endpoint elevations, reversible ascent continuity, tread limits, sample spacing and maximum actual ramp slope passed
- Generator group restoration and preservation of random state passed

Added geometry: **158,352 visual + 105,284 collision = 263,636 triangles**. Lighting metadata contains **182 lantern fixtures** and **178 connected wire runs**. Fixture-only legacy triangles are excluded from these added-geometry totals.

This is an offline geometric pass. It does not establish Unity CharacterController, Udon, VRChat runtime, final-world obstacle clearance, or visual absence of branches and foliage across the route.

## Final whole-world verification

After integration and regeneration:

```bash
python Source/validate_crown.py
```

The owner must run this against the regenerated manifest, actual full `CollisionMeshes.bytes`, and every `solidBoxes` obstacle, with the updated expected crown height. Include the original safety walls after attachment cuts, the elevated alley shops, new pump equipment and all other colliders. Run the project's navigation, infrastructure and world regressions as well, then visually inspect the arrival, north bridge, entire ascent and crown approach.
