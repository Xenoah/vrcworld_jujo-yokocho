# v2.16.0 — Eight individually designed venues

Unpublished editable-source candidate. Five food venues and three nightlife venues replace the repeated shop shell, furnishings and signs. See [the venue roster and preservation boundary](ShopPersonalityDesign.md).

## Measured whole-world source budget

| Metric | v2.14 | v2.15 | v2.16 |
|---|---:|---:|---:|
| Visual vertices | 3,200,270 | 3,151,124 | 2,692,303 |
| Visual triangles | 2,649,607 | 2,646,359 | 2,296,853 |
| Source visual batches | 1,058 | 1,058 | 1,106 |
| Native visual bytes | 108,651,058 | 107,432,578 | 92,234,539 |

Current compressed native payload is 29,448,965 bytes; editable GLB is 121,525,064 bytes. These are source file measurements, not Unity serialized size, VRChat download size, draw-call measurements or FPS. Distinct material/component batches increase by 48 despite the geometry reduction. No blanket forest decimation was used.

## Preserved and intentionally changed

- All 815 nonshop visual batches, exterior collision binary, floors, stairs, fall barriers, unrelated lights and five unrelated explicit collider boxes are exact to the accepted v2.15 checkpoint.
- All 49 station IDs remain, but interior positions, facing and exits change. The 98 shop collider boxes match the new furniture and counters; do not call all collision metadata unchanged.
- Original herb planters and underside supports remain exact. The final bottle detail pass changes only the approved snack/cocktail component rows, while bounds, materials, seats, routes, solids and lights stay exact.
- Two new 2048px sign atlases remain lossless in the editable GLB. Existing shader code is unchanged; eight named materials receive narrowly additive opaque material routing.

## Review and remaining validation

Independent final source preservation, 208 required clearance probes, 49 connected exits, GLB scene/material/array preservation and exact revision-oracle capture pass. Full regression and clean-extract status is recorded in the accompanying validation outputs, not inferred from these component checks.

The all-eight preview gallery predates the final small bottle-detail change; final interior previews use the final GLB. Blender uses approximate shader and lighting behavior, including live point highlights unlike the target baked Unity lights. No Unity/Udon/shader compilation, baking, VRChat runtime, stereo or device-performance result is claimed.

Rebuild the complete matching scene, then lighting and reflection probes. Do not install only new visible meshes into an older scene with stale station positions and phantom counter colliders.
