# Distance-aware cost audit, no geometry changes

Input is the accepted first optimization native payload, SHA-256 1813e16aede8f59fb34e200ee276034521470f96e693ddd034ed66810e9cb133. The audit reads 1,058 batches, 46,932 exact-position connected diagnostic components, 4,733 floor-probe eyes, and the actual crown/deck route polylines. Diagnostic position grouping never changes export vertices or material boundaries.

## Actual expensive families

| Family | Triangles | Nearest sampled eye to an actual vertex |
|---|---:|---:|
| Host crown folded leaves | 401,760 | 0.63 m |
| Opaque forest grove crowns/conifers | 289,324 | 170.08 m |
| Shop CraftSurfaces | 131,554 | 1.82 m |
| Grove alpha sprays | 110,872 | 18.91 m |
| Host framing folded leaves | 106,920 | 1.72 m |
| Shop clay roofs | 101,600 | 1.50 m |
| Peer alpha sprays | 67,794 | 10.83 m |
| Grove twig tubes | 66,736 | 22.38 m |
| Hanging-lantern bronze ribs/caps | 54,694 | 1.00 m |
| Peer twig tubes | 48,824 | 14.80 m |
| City roof timber details | 15,012 | 543.64 m |

These are sampled-eye/vertex distances, not visibility tests or a guarantee of continuous-route minimum. For candidate selection, a second pass computes exact component-center distance to continuous route-eye segments, then subtracts the complete component bounding radius, route half-width and 0.30 m tread margin. That gives a conservative corridor-envelope bound. It does not cover arbitrary flight or every off-route deck viewpoint.

## Findings that change the optimization decision

- The old scenery source comment claiming all leaf cards are at least 59 m away is no longer valid after crown traversal. West peer sprays reach 10.83 m from an authored floor-probe eye. `Near`/`Far` names are authoring/culling partitions, not LOD or distance guarantees.
- West/East peer `Near` groups mix different distances. `AncientPeers_West_Far` starts at approximately 489 m and East_Far at 540 m in sampled measurements, but together they contain only 19,068 triangles. They are not the largest cost.
- The biggest family, 21,195 host folded leaves totaling 508,680 triangles, is not a safe distant target without LOD. No component has a conservative route-corridor separation of 50 m; only 210 crown leaves clear 30 m, and no framing leaves do. Typical leaf bounding diameters are tens of pixels in a 1280-wide/60-degree reference view. Keep the folds, serration, coverage and normals.
- Grove alpha sprays are already two triangles per card. Reducing their count is coverage removal, not planar simplification. The closest sprays are substantial silhouette elements. Leave them unchanged.
- Lantern rib geometry is expensive but close: bronze rib/cap components are all within 10 m by conservative component envelope. Blanket tube simplification would remove visible craft.
- Most flat architecture is already minimum two-triangle quads. The distant city timber detail has 1,251 ordinary 12-triangle boxes, not subdivided flat grids. Removing coplanar subdivisions cannot shrink those boxes while keeping all six faces.

## Ranked bounded opportunities

### 1. Exactly hidden city bracket top caps: strong geometric proof

All 834 bracket top quads, in one exact batch (`Landscape/DetailCityRoofs`, `DarkTimber`), are enclosed inside their associated opaque fascia boxes. Actual native corner coordinates give at least 55.255 mm clearance to every fascia boundary. Because each fascia is convex, containing all four cap corners also contains the entire two-triangle cap.

Potential saving: 1,668 triangles, 3,336 vertices, 100,080 raw native bytes. These are exact prospective counts, not yet a delivered optimization in this audit. Each cap owns four independent vertices, so surviving side-face normals, UVs and colors can remain exact. Neither skyline, foliage coverage nor collision needs to change. Still require a separately gated one-batch revision, independent enclosure and surviving-attribute tests, unchanged bounds, and exterior-view/shadow review. See hidden_city_caps_audit.json for every explicit face range.

### 2. Only remote twig stem cross-sections: bounded investigation, not approved

There are 1,162 grove and 1,214 peer three-ring/five-sided stems whose entire conservative route-corridor envelopes are at least 100 m away. Four-sided forks and all leaf cards can remain untouched. Changing only those stems from five to four sides would reduce 30 to 24 triangles and 20 to 17 vertices per stem.

Potential saving: 14,256 triangles, 7,128 vertices and 342,144 raw native bytes. No gzip or runtime saving has been measured. The ring-profile radial error bound is below approximately 0.160 reference pixels for grove stems and 0.337 for peer stems at 1280×720/60-degree horizontal FOV, including off-axis perspective margins. This is NOT a complete loft, shading, normal or UV certificate. Full native facet/normal comparisons and multiple reachable-view tests remain necessary. Do not apply it to whole `Near` groups: nearby peer stems can be only 14.8 m away. Geometry remains on hold.

### 3. Larger opaque forest crowns: meaningful budget, substantial visual risk

There are 1,667 120-triangle grove crowns, plus already coarse 24/20/28-triangle crowns/conifers. Of the 120-triangle crowns, 1,078 clear a 300 m corridor envelope, 589 clear 400 m and 235 clear 500 m. Reducing 12 to 8 angular samples could theoretically save 43,120 / 23,560 / 9,400 triangles at those respective thresholds.

These are upper opportunity estimates, not approved savings. The source has deliberate three- and seven-lobed profiles, and projected crown diameters are still tens of pixels. Lower angular sampling can alias those lobes, change skyline/coverage, and alter normals. No safe error bound has been demonstrated. A blanket forest decimation is not justified by this audit.

## Explicit exclusions

No LODGroup implementation, geometry edits, collision edits, material/coverage changes or protected-payload exceptions are part of this audit. Mountain detail owns twelve disjoint SnowRange batches and is not touched. All source savings above are estimates until an isolated candidate is generated and independently admitted. No FPS, GPU timing or Unity/VRChat runtime performance claim is made.


## Reproduction and report size

This is a dated read-only audit of native SHA `1813e16aede8f59fb34e200ee276034521470f96e693ddd034ed66810e9cb133`, before later mountain/city-cap revisions. Its candidate figures are not final delivered counts. The compact summary is `geometry_cost_candidates.json`. Full per-component JSON reports are generated locally rather than adding approximately 80 MB of diagnostic text to the source package.

From project root, run:

```sh
python Source/audit_distance_cost.py . Docs/native_cost_distance.json
python Source/audit_route_components.py Docs/native_cost_distance.json Assets/TreeTopYokocho/Data/WorldManifest.json Docs/continuous_route_cost.json
python Source/summarize_candidates.py Docs/continuous_route_cost.json Docs/geometry_cost_candidates.json
```

Running against a later source revision produces that revision's evidence, not an automatic reproduction of the frozen audit above. Retain the input native hash with the report.

## Distance correction

The earlier informal combined “1.7–1.8 m host foliage” description mixed the crown and framing families. Using the same nearest exported-vertex to authored floor-probe eye metric, crown reaches 0.628999 m and framing 1.724844 m. Both use shoulder probes, not separately body-clear certified cameras. These values are neither a universal legal-view minimum nor continuous-route distance guarantees. Exact points and definitions are in `geometry_distance_reconciliation.json`. The optimization decision remains to preserve near foliage craft.
