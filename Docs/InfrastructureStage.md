# Tree utilities and open Noh-inspired stage

These are two independent, visual-only authoring modules. They can be enabled separately in the world builder, before `Geometry.compact()`. They do not create collision, change `layout.reference.json`, or install runtime components.

## Utilities: `Source/tree_infrastructure.py`

Call `add_infrastructure(g, M, rng, layout=layout)` with the builder's **working** layout. Omit `layout` only when the original reference paths/stairs are authoritative. The function restores `g.group` and returns JSON-safe data:

- `beacons`: individual warning-lens groups, exact imported renderer names, source coordinates, pulse timing and lightmap exclusions
- `lights`: 52 warm path/ring lights with the original reference layout, intended for baking only; the count can change with working-layout stair exclusions
- `utilityRoutes`: water, gas, electrical and telecom route centerlines
- `poleBases`: actual lamp-post footprint positions for visual/intersection QA
- `stats`, `serviceReservation`, `collisionAuthored: false`, and integration notes

The geometry includes blue water and ochre gas risers, protected electrical and telecom risers, 82 pipe clamps, tree saddles, junction boxes, below-deck distribution loops, outboard timber lamp posts, supported overhead wires, a compact root-level pump/electrical bank, and a braced upper-trunk telecommunications tower. Connections include rounded elbows and explicit pole-to-conduit feeds; no wire is intentionally laid across a walking surface. Existing shop and path dimensions are not changed.

Ground service reservation: X −23.2 to −19.2, Y −20.3 to −17.3, source Z −4.25 to 2.0, west of the existing lift. This is an equipment plinth, not a proposed public floor. Ground supply routes turn north of the lift through approximately Y −14.05 to −13.59. Trunk risers follow azimuth 228°, outside the procedural bark. New ground stairs must be checked against these reservations before final integration.

### Flashing warning lights

`AviationRed` declares `shader: "Beacon"`, emission 4.5. The parent-authored `TreeTopYokocho/Beacon` shader animates emission using Unity `_Time`: 2-second period, 0.16 duty, phase 0, with short smooth rise/fall edges. The Python/glTF/Blender preview shows a static ON state. Runtime flashing needs the Unity builder to select that shader; it must not silently fall back to a permanently emissive Surface material.

Exact lens renderers and source coordinates:

| ID | Renderer | Position X, Y, Z |
| --- | --- | --- |
| Apex | `Mesh_Infrastructure_WarningBeacons_Apex_AviationRed` | −2.9, −4.7, 124.965 |
| Mid | `Mesh_Infrastructure_WarningBeacons_Mid_AviationRed` | −3.6, −4.7, 105.815 |
| Lower | `Mesh_Infrastructure_WarningBeacons_Lower_AviationRed` | −2.18, −4.7, 95.015 |

Each group is `Infrastructure/WarningBeacons/<ID>`, under `Visuals/` after import, and contains only its lens. The mechanical cage and dark housing are in separate static geometry. Exclude lens meshes/materials from baked emission and GI; do not bake a permanent red light patch. The shader does not need an Udon update loop or extra real-time point lights. Returned range/strength/color fields are descriptive optional light settings, not requests to spawn lights. Unity coordinate conversion remains `(x, z, y)`.

### Reference-layout cost

- 40,680 added triangles, 64 material/group batches
- 52 lamp posts, 12 junction/equipment boxes, 82 pipe clamps
- 3 telecom panels, 1 dish, 3 independently identified warning lenses
- No added collision triangles

Materials reuse existing wood, iron, stone, ceramic and roof materials where appropriate; eight compact solid-color utility materials are added.

## Stage: `Source/noh_stage.py`

Call `stage_layout()` before generating deck/floor boundaries. The stage center is `[10.111627, 10.111627, 40]`, radius 14.3 m at 45°, facing northeast/outward. The visible cypress performance floor is 4.2 × 4.2 m. The stage sits in the northeast gap between the trunk and ring, rather than at the occupied origin.

The floor is a flush 12 mm cosmetic finish over the continuous Z40 deck. Four posts support a hipped roof with exposed rafters and cedar brackets. A small pine crest sits high on a rear transom; there is no eye-level opaque rear wall. All four sides remain open. The nearest deck edge is 11.6 m from the original trunk origin. Four solid-post collider recommendations are provided explicitly; the visual function never applies them.

Recommended integration sequence:

```python
from noh_stage import stage_layout, add_noh_stage
from tree_infrastructure import add_infrastructure

stage_spec = stage_layout()
pieces[stage_spec['level']].append(Polygon(stage_spec['deckUnionPolygon']))
# Continue the existing floor union, stair cuts, floor meshes and boundary guards.
# This removes obsolete inner-hole guards at the newly connected stage apron.

stage_result = add_noh_stage(g, M, rng)
solidBoxes.extend(stage_result['solidBoxes'])
floorTests.extend(stage_result['floorTests'])

infra = add_infrastructure(g, M, rng, layout=layout)
lights.extend(infra['lights'])
# Persist stage_result and infra metadata as appropriate for the parent manifest.
```

Deck-union polygon in X/Y coordinates, in order:

1. `[5.975052, 10.429825]`
2. `[10.429825, 5.975052]`
3. `[14.637110, 10.182338]`
4. `[10.182338, 14.637110]`

Do not add this polygon only after guards have been generated, or the existing invisible inner-ring wall would block entry. Preserve the continuous physical slab at Z40. The entire central radius-18 circulation line stays clear of stage posts. The post bases and 2.68-m-high knee brackets do not occupy the ring's ordinary walking volume. The roof maximum is Z44.265, below the upper level; the footprint does not intersect original stairs.

The stage returns `floorPolygon`, `deckUnionPolygon`, `solidBoxes`, `floorTests`, `visualBounds`, `stats` and layout notes. `stage_layout()` performs no geometry mutations; `add_noh_stage` restores the previous group. Stage cost: 2,256 triangles, 12 material/group batches, one new cypress material copied from the existing Counter PBR setup.

## Checks completed

- Python compilation and independent function invocation
- Finite vertices and UVs; triangle indices in range; material names resolved; no zero-area triangles in either module
- Geometry compaction, normal-map UV repair and mood-color generation
- Stage floor completely covered by proposed deck; no overlap with original stair corridors
- Proposed stage deck minimum distance to the nearest original L2 shop: 8.33 m
- Warning groups contain exactly one lens/material mesh each and exact renderer identifiers match the importer's naming convention
- Group state restored after each call; metadata is JSON-serializable
- Scratch Blender geometry previews inspected for stage, utility routing and telecom mast

These checks do not constitute Unity shader compilation, in-client flash timing verification, integrated new-stair clearance validation, light baking, or VRChat runtime testing. Those remain integration/runtime checks owned by the main world task.
