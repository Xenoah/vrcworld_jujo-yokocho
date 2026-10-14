# v2.19.0 — Projecting signs and cloth pennants

This unpublished production-source revision adds actual three-dimensional signs to the eight distinct RPG venues. It follows the independently verified v2.18 moonlit tea-pendant checkpoint. It is not a compiled or uploaded VRChat world.

## Street-facing identity

- 竜の熾火亭: dimensional dragon-and-ember shield.
- 風渡りの麺工房: noodle bowl, raised noodle/chopstick detail and forked cloth pennant.
- 旅人の燈火亭: hanging traveler’s pot with real handle and dimensional inset.
- 宵闇の魔女: crescent and witch-hat emblem, plus pointed wine-colored pennant.
- 月詠みの茶房: a thick framed timber blade sign, pale wooden moon/cup relief over darker chestnut, visible grain, through-pegs and connected suspension.
- 星屑の蒸留所: dimensional bottle and raised star medallion.
- 吟遊詩人の隠れ家: open, genuinely shaped lyre with separate strings.
- 妖精の菓子工房: winged confection/gift emblem and scalloped cloth pennant.

The principal RPG names, Japanese typography, venue lighting and interiors remain intact. Signs project along the street rather than simply duplicating a flat face-on title. The cafe sign is placed to expose its relief from both tested oblique approaches. Each existing post/roof is preserved; only new brackets and sign bodies are positioned around it. Final forward projection is at most0.70m beyond the frontage line, and the lowest new point is2.309m above its venue floor.

Only S02, S04 and S08 receive pennants, with different hems and restrained static folds. These are closed4mm cloth shells, not animated transparent planes. Existing materials and shader settings are reused; no light, new material definition, texture, shader, strobe or wind animation is added.

## Measured cost and preservation

The new signs add7,652 triangles,16,290 exported vertices and38 source batches. Same-material pieces are concatenated per venue without welding, reducing the initial57 semantic/material batches to38 while retaining a precise component range ledger.

The complete world has1,145 source batches,2,708,881 vertices and2,304,649 triangles. Compared with the initial verified v2.14 source, this is491,389 fewer vertices and344,958 fewer triangles, but87 more source batches. These source counts are not measured draw calls, FPS, runtime memory or Unity download size.

The native material roster remains130 definitions. Previously unused Noren1 and Noren3 become visible on two pennants, using their unchanged existing Cloth routing and woven maps. The editable GLB consequently includes two additional used-material entries and one existing woven ARM image. The wine pennant retains its existing Cloth routing with procedural weave disabled. The two Noren pennants use physical UV density near4repeats/m, yielding about2.6mm procedural periods at their unchanged weave96 setting, subject to filtering. Runtime visibility and VR shimmer remain untested.

Every one of the prior1,107 native batches is protected. Original GLB accessors, materials, image semantics and scene placement are separately checked. Main signs, all49 stations/exits, routes, explicit colliders, collision meshes, guard walls, original materials and all light settings remain unchanged.

## Validation boundaries

The model audit checks every new decorative-body triangle against every original venue triangle, excluding only named structural/suspension hardware whose intentional contacts are checked separately. All eight bodies have zero such intersections; all13 suspension links contact their sign and support. This local authoring test is distinct from the full-world route check, which includes every added triangle without a sign exclusion.

Full-world source clearance uses the existing208 required probes and49 station connections with their documented body envelopes. It is not arbitrary-avatar, roomscale, hand-reach or headset certification. Exact after-art admission and archive clean-extraction results are recorded separately in the validation sidecar after completion.

Actual-model Blender previews use the production geometry and source light palette. Cycles live point lights, its BRDF, camera-only emission and display mapping differ from Unity baked lights/probes. Unity compilation, baking, VRChat Build & Test, avatar calibration, stereo and performance remain untested. Remote publication is still paused; this is a local source deliverable.

## Visual QA limitation
The cafe's timber blade and cup/moon relief are physically modeled and visible at close range, but the existing roof shade makes the emblem hard to identify from the inward street approach. The main RPG fascia remains readable. No extra light or preview-only brightening was introduced to conceal this limitation. Recheck the sign under actual Unity baked lighting and reflection probes before publication; approach-distance emblem legibility is not claimed.
