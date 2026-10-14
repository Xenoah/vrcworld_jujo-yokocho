# Visual mesh optimization checkpoint

This is a measured source/native/GLB optimization, not a Unity runtime or FPS claim.

| Measure | v2.14 source | Optimized source | Reduction |
|---|---:|---:|---:|
| Visual vertices | 3,200,270 | 3,152,231 | 48,039 |
| Visual triangles | 2,649,607 | 2,644,271 | 5,336 |
| Visual batches | 1,058 | 1,058 | 0 |
| Native bytes | 108,651,058 | 107,434,090 | 1,216,968 |
| Gzip bytes | 33,062,783 | 32,947,546 | 115,237 |
| Editable GLB bytes | 139,416,948 | 137,720,652 | 1,696,296 |

## What changed

1. Remove 45,371 unreferenced visual vertices from 128 exact batches. Preserve 34 otherwise-unused extrema anchors so every original culling AABB is bit-identical. This is not welding: the order and attributes of every rendered triangle corner, vertex-sharing equivalence classes, material identities and all normal/tangent seams are unchanged.
2. Replace four exactly planar distant sea grids with constrained triangulations using every original boundary sample. Each sector changes from 775 vertices / 1,440 triangles to 108 vertices / 106 triangles. Ordered boundary-edge position, UV and Color32 bytes are unchanged, polygon domain is identical, and all normals remain vertical. Sea UVs are affine; maximum original float32 storage error is 8.057e-6 UV units, giving a conservative interpolation-difference bound of 1.612e-5. Arbitrary painted UV fields are rejected.
3. Coordinate the sea with the reviewed Water shader: the old undersampled 43 mm vertex waves become world-space animated fragment ripples on a static mean plane. Mesh admission requires the exact approved non-displacing Water source SHA in both manifest metadata and the actual shader file. This is an intentional animation representation change, not a claim of identical animated geometry.

## What did not change

- Collision bytes and gzip are byte-identical. Collision SHA-256: 51e395fbea8f6d29ffbebe76bb484f465c671508f93bf75afa9294ccff630ddb.
- All 49 station records and the complete navigation, floor/wall probes, guard, spawn, stair, lift and safety definitions are unchanged.
- All non-sea rendered triangle positions, UVs, Color32 values, ordering and vertex adjacency classes are exact.
- GLB normals for every corresponding non-sea rendered corner are bit-identical, with maximum component difference zero. Sea normals are exactly +Y in glTF.
- No foliage alpha geometry, cloud silhouette, timber bevel, roof tile lip or collider wall was decimated.

## Why the reductions are restrained

Most high-count flat architecture already consists of minimal two-triangle quads or intentional bevel facets. The large tree and leaf families carry silhouette or normal information. Flat-looking input is not automatically safe to decimate, particularly with animated vertex shaders. The clear redundant grid was the distant sea; the largest lossless savings were unused pole/repair vertices in tree crowns and framing.

## Sea viewpoint evidence

The entire collision XY bounding box, expanded by one metre, is at least 302.803 m horizontally from the sea. Replacing the old 43 mm vertex displacement has a conservative full-frustum perspective bound of 0.226604 pixels for a 1280×720, 60-degree horizontal-FOV camera, including diagonal/off-axis and displacement margins. This does not cover arbitrary flying cameras, VR lens distortion or Unity runtime shading.

The nearest passing sampled source viewpoint is:
- Eye: [10.8828126864435, -38.49109491858843, 29.67501221982725]
- Sea target: [105.0, -339.6689758300781, -4.019999980926514]
- Distance to sea: 317.335 m.

The established [0, -40, 135.65] viewpoint also passes. Both have continuous projected 0.25 m-radius floor support; 17 supporting-height probes; and no finite body-cylinder contacts against all 1,141 visual/collision meshes and 77 explicit boxes from highest footprint support +0.06 m to +2.2 m. Exact source hashes, triangles and barycentric coordinates are in the diagnostic report. These are offline geometry checks, not Unity capsule sweeps or visibility/occlusion tests.

## Contract preservation

The immutable 132-row optimization oracle contains exact before/after payload hashes. Only literal feature flags admit their corresponding exact after payloads. Actual export counts are checked before those rows are projected to prior summaries for the older immutable contracts. No family, prefix, tolerance or blanket exception is introduced. All original 59 noren Identity batches and 107 indexed component slices remain untouched and are checked on the real optimized native bytes.

Historical synthetic feature-matrix tests need a pre-optimization fixture. A separate test-only inverse archive restores removed vertex attributes and original sea data, then requires the entire reconstructed native file to hash exactly to frozen v2.14 SHA d622d11830fb0d946c1b41301ffbe409e213283329013e3ae5a30b447f6f5b78. Production admission never calls this inverse helper.

## Reproduction

Using the pinned authoring environment:

1. Run `python Source/build_world.py` to generate both native and GLB from source. The optimization hooks run after UV repair and color bake, before both exports; collision geometry never enters them.
2. Run `python Source/pack_geometry.py` to create checked gzip transport shards.
3. Run `python Source/run_checks.py` for the complete offline regression suite, including mesh and exact optimization-contract tests.
4. Compare the resulting native visual SHA to 1813e16aede8f59fb34e200ee276034521470f96e693ddd034ed66810e9cb133 when no other geometry changes are integrated.

The source-only optimization feature flags are `visual_unused_compaction` and `static_planar_sea`. The approved Water source SHA is a6f80b12ed3ac8c4e147d4f25a3bd659488600b018cfd273880942f5d5289e6b. A later Water change requires a separately reviewed compatibility revision, not disabling the guard.


## v2.16 shop replacement scope

The individually designed shops supersede the prior repeated shop shell and 107 historical noren slices. Those older invariants remain historical inverse tests, not descriptions of current shop geometry. Current admission uses the exact 291-row v2.16 oracle and actual clearance checks. Nonshop shader/geometry preservation remains separately enforced. See [ShopPersonalityDesign](ShopPersonalityDesign.md).
