# Dimensional venue signs: frozen candidate 05

Authoritative additive module: `Source/venue_projecting_signs.py`.
SHA-256: `bd87b5c7fe5aae22f96e8b608a63bff56c7f9caadbb568e11c5b02dded3cf6f5`.

Call `add_signs(g, P, idx, M, w, dep)` after the complete original venue has been authored. `idx` is zero-based. Integration is implemented in the world builder, not in the unchanged venue dispatcher. The call restores `g.group` and only adds `Shops/Sxx/ProjectingSigns/<Motif>Assembly` batches. It does not author, change or return colliders, seats, lights, textures, material definitions or font data.

All eight original principal names and sign art remain untouched. The additions are a dragon/ember shield, noodle guild bowl, traveler pot, witch moon/hat, timber moon/tea plaque, star bottle, open lyre and winged confection. Only S02, S04 and S08 receive cloth pennants, with forked, pointed and scalloped hems. These are static, closed 4 mm shells with low-resolution broad folds, not animated one-sided planes.

S05 uses a real 92 mm timber frame, an inset chestnut panel, pale timber moon/cup relief, through-pegs and a physically connected post bracket. It is a double-sided blade facing along the street, not a duplicated front title. Its outer projection is 0.70 m beyond the post/frontage line. The last neutral two-approach preview uses the unchanged candidate-04 S05 geometry; S05 is exactly unchanged in candidate 05. Integrated cool-night previews and source-supported human-eye camera validation are recorded separately.

## Final geometry

| Venue | Triangles | Batches | Maximum forward reach | Minimum local Z |
|---|---:|---:|---:|---:|
| S01 | 676 | 5 | 0.660 m | 2.315 m |
| S02 | 956 | 6 | 0.668 m | 2.312 m |
| S03 | 644 | 5 | 0.654 m | 2.3325 m |
| S04 | 784 | 4 | 0.650 m | 2.3174 m |
| S05 | 1,432 | 4 | 0.700 m | 2.315 m |
| S06 | 844 | 4 | 0.650 m | 2.315 m |
| S07 | 764 | 3 | 0.649 m | 2.309 m |
| S08 | 1,552 | 7 | 0.640 m | 2.342 m |
| Total | 7,652 | 38 | | |

Existing materials only. Noren1 and Noren3 become used by the new pennants; their descriptors and existing textures remain unchanged. This activates two GLB material entries, not two new native material definitions. S04 reuses the existing wine upholstery material and its existing shader routing. No point lights, transparency, motion, or new textures/shaders were introduced.

## Exact consolidation and metadata

The original 57 semantic/material batches are concatenated, without welding or other mesh modification, into 38 per-venue material batches. A deterministic component range ledger preserves every semantic part and support role.

Each returned record has `shop`, `root`, `localBounds`, `dimensions`, `triangleCount`, `sourceVertexCount`, ordered `keys`, `batchCount` and one actual assembly `parts` row. That row's `components` include semantic name, role, exact original bounds/counts and each original material's vertex/triangle slice in the consolidated batch. After UV repair, recover components by `triangleStart` and `triangleCount`: faces retain order, while vertex indices may be split/remapped. The vertex range is explicitly a source-authoring range, not a promise about repaired export indexing.

## Validation shipped in frozen candidate

- Ten portable unit tests PASS: additive scope, immutable materials/mapping/group, deterministic output and unchanged RNG, rigid transform covariance, finite outward closed geometry, current dimensions/headroom, post contact, duplicate rejection and exact consolidation range reconstruction.
- Every actual decorative-body triangle versus every old venue triangle: all eight venues have zero intersections. Only explicitly identified support hardware is excluded from this mechanical body check. This does not remove hardware or any other triangle from world route/clearance tests.
- Every one of the 13 suspension links has actual triangle contact with its own sign body and supporting bracket.
- All three whole cloth material meshes are watertight and consistently outward. At unchanged weave96, the new 4-repeats/m UVs give measured median procedural periods around 2.61 mm for Noren1/3. The wine material keeps its existing Cloth routing with procedural weave disabled (_WeaveStrength=0). Its reported 96-cycle period is a theoretical UV diagnostic, not an enabled procedural effect. This is not a claim about visible runtime micro-weave or VR aliasing.
- Body collision fixes cover the actual curved Oden roof seam and sloped S04 rafters, not only fascia AABBs.

Commands from a complete matching project root:

    python Source/test_venue_projecting_signs.py
    python Tools/audit_projecting_body_intersections.py .
    python Tools/audit_projecting_support_contacts.py
    python Tools/audit_projecting_cloth_uvs.py

The body diagnostic rebuilds unchanged original venue geometry using the supplied root's manifest material definitions. It never writes that baseline or modifies original source. It writes reports only beneath this tool's own project root.

The final frozen folder includes exact geometric metadata, literal per-component frontage slots, reports, test material fixture, portable audit scripts and a SHA-256 manifest. Use those files, not preliminary-01/02/03 or candidate-04.

Unity import/compile, runtime lighting, VRChat build, avatar/headset testing and actual runtime frame/draw performance are not claimed by these source tests or Blender previews.
