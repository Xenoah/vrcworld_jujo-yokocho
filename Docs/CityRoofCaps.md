# One-batch enclosed city cap optimization

This candidate adds only the literal `city_roof_hidden_caps: true` feature. It removes 834 bracket top quads from `Landscape/DetailCityRoofs / DarkTimber`, not exposed faces, entire boxes, foliage, collision or near craft. Source hook runs after color/UV baking and existing optimization, before both native and GLB export. False, omitted and nonboolean flags never authorize the changed payload.

## Geometric certificate

The original batch contains 139 houses, each with nine independently faced boxes. Each of the six bracket caps per house lies strictly inside its associated fascia. Source validation verifies exact box topology, closed outward-wound fascia shell edge incidence, convex actual-triangle halfspaces, every cap corner inside all halfspaces, and at least 50 mm clearance. Independent review measured minimum 55.255066 mm. Convexity contains the complete removed triangles, not just their vertices. All external rays intersect the unchanged opaque fascia before any removed cap.

Surviving ordered triangle corners, position/UV/Color32 bits and vertex equivalence classes remain exact. Each cap uses its own four vertices, so removing cap-only vertices does not remove normal contributions to any surviving vertex. Original bounds are unchanged. Tests compare actual exported GLB normals, UVs, colors and positions, not only recomputed estimates. Actual collision raw and gzip data, all 49 seats, routes and navigation metadata remain byte-identical.

Expected source counts for the one batch: 30,024 to 26,688 vertices; 15,012 to 13,344 triangles. Native saving 100,080 bytes. Measured gzip and GLB savings are recorded separately in Measured/preservation.json after regeneration. No FPS, GPU or Unity runtime claim.

## Dependencies, deliberately fail closed

The exact original/after batch and DarkTimber descriptor are frozen in a new single-row oracle. The existing 132-row optimization oracle and every older peer/noren oracle stay unchanged. Production admission authenticates actual after payload first, then normalizes only this one row to its already-frozen original summary before the existing 132-row normalization. Actual export counts are checked before projection.

The opacity/enclosure proof requires the same static opaque Surface shader, material routing, and Landscape shadow/lightmap behavior. Therefore admission also pins the full reviewed Surface source, world builder, FantasyMaterials profile and profile loader. This is intentionally stricter than checking a few source strings: a future shader-routing edit anywhere in the builder must be reviewed and explicitly compatibility-repinned. The fantasy profile routes DarkTimber to Surface with only grain roughness; no transparency or vertex movement. The current builder excludes Landscape from shadow casting and lightmap unwrap, unchanged here.

The integration owner plans a disjoint mountain-normal import helper that will change the builder hash. That change is NOT automatically admitted. Review the new builder and explicitly update only its compatibility digest in contract and generated metadata. Never regenerate/replace the geometry oracle for a compatibility-only change.

Test-only inverse restores the exact city batch first, then invokes the unchanged 132-row inverse and its original whole-world native SHA check. It is never imported by production admission. Mountain inverse, if enabled, must also run before that final whole-world check.

## Limits

This is a source/native/GLB preservation certificate for static opaque rendering. No claim of Unity compressed-mesh or GI bake pixel identity is made. Runtime import, VR stereo and GPU measurements remain unavailable. Open cap holes are inside solid fascia, not on any externally visible silhouette. Nothing changes collision, navigation, leaf coverage or exposed craft.

## Reproduce

Use the existing tree-venv Python. Run Source/build_world.py against this isolated candidate root, then Source/test_city_roof_caps_contract.py and Source/measure_city_caps.py with the accepted first optimization root and this candidate root. Run Source/test_visual_optimization_contract.py, Source/test_peer_culling_contract.py and Source/run_checks.py. Do not run against frozen baseline symlink overlays. Apply only explicit hook patches and new files during integration; never overwrite concurrent mountain or shader source wholesale.


## Reviewed import precision revision

The selected combined builder explicitly sets MeshCompression.Off only for the exact `Landscape/DetailCityRoofs` / `DarkTimber` mesh when `city_roof_hidden_caps` is true. Source-space55.255mm enclosure is not treated as a guarantee under unspecified Low quantization. Meshes remain readable Float32; no UploadMeshData(true) path is introduced. The separately reviewed12 mountain seam meshes also use Off; all other visual meshes retain Low and collision geometry is unchanged.

Whole-builder dependency was explicitly repinned after independent source review to `b1457615342413a2f099308920883169ec5aec88c39b932511a4e8fd0a10c119`. The cap geometry oracle is unchanged. Uncompressed serialization may increase Unity asset/build size relative to Low; this has not been measured. Source/native byte savings and triangle reductions do not imply a smaller Unity download or measured FPS improvement.
