# Forest, fortified city, snowy range and southern sea

`Source/fantasy_landscape.py` is the replacement visual landscape generator. Its `landscape(g, m, rng)` signature matches the former generator; no new Python dependencies or textures are required.

## Geography

- A continuous, gently rolling mainland now runs beneath the tree and forest. The original central bedrock mesh is preserved, including all vertex positions and faces. Added surface within 30 m of the origin lies underneath it at Z=-1.65 m
- Sixteen ancient peer trees, approximately 114–139 m to their crown tops, flank the world in asymmetric groves. Buttress roots, branching trunks and broad lobed crowns make them comparable to the main 120 m tree
- An approximately 641 m winding road runs north from the G0 west edge to a circular fortified city centred at source XYZ (0, 740, 12). The curtain wall has a 162 m radius, an open south gate, 18 towers including the central keep, and approximately 137 houses
- Seven snow-capped peaks lie beyond the city. The clipped snow boundary and shared slope vertices avoid disconnected snow caps and per-triangle checkerboard shading. Mountain edges merge below the mainland surface
- The south opens onto a sea with six layered islands. Every island joins the water below Z=-4.02; none is an airborne island

## Performance and boundaries

- Distance-tiered opaque tree meshes, spatial batches, and reused textures protect the detailed shops' budget. No new alpha foliage, realtime lights, downloaded assets, or distant colliders are added
- Eight small material definitions reuse existing textures or plain colour. Canopies use plain opaque colours plus vertex mottling, avoiding enlarged leaf-vein stripes. Closed single-pole meshes eliminate the previous crumpled crown-top gaps. The scene contains 2,724 trees including the 16 giants and 138 island trees; near/far split and exact houses vary with the caller's random-stream state
- The isolated seed-12040 run produced 523,804 scenery triangles in 119 material batches. The authoritative integrated counts are returned in `WorldManifest.detail`
- Source geometry size is not the compressed Windows world download size. The approximately 50 MB target still requires an actual Unity/VRChat Windows build measurement
- Traversable ground, G0's graded connection, safety walls and collisions remain owned by the main world builder. The visual road begins at XY(-27,-34), approximately Z=-1.52, while G0 is Z=0
- `terrain_height(x,y)`, `road_points()`, `ROAD_CONTROL`, `CITY_CENTER`, `CITY_RADIUS` and `SEA_LEVEL` are exported for integration

## Suggested source-XYZ views

- North panorama: position (-24.5,23.4,53.75), target (0,740,40), lens 26–32 mm
- City detail: same position, target (0,740,60), lens 60–65 mm
- Southern sea: position (-24,-30,53.75), target (0,-1450,30), lens 28 mm
- Layout overview: position (700,-900,950), target (0,340,0), lens 28 mm
- Use a far clipping distance of at least 6,000 m. Existing exponential-squared fog at 0.00085 hides the mountains; approximately 0.00025–0.00030 preserves distant silhouettes

## Verification

Isolated Python geometry checks confirm finite positions/UVs, valid triangle indices, no zero-area faces, watertight crowns with outward normals, and exact preservation of the original central bedrock vertices/faces. Isolated Blender scenery previews were used to inspect north/city/south/aerial composition and fix the mountain-foot seam and sparse foreground. These are material/geometry previews, not Unity or VRChat runtime tests. Full generation, integration and Windows build verification are separate steps.
