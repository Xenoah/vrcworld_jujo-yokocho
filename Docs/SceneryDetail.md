# Scenery surface-detail pass

`Source/scenery_detail.py` provides `add_scenery_detail(g, M, rng)`. Call it immediately after `landscape(g, M, rng)` and merge its returned dictionary into the manifest detail data, before `compact`, mood colours and normal-UV repair.

## Changes

- Finds the actual indexed crown meshes within 430 m of the main tree, regardless of the upstream random-stream state. Slightly smaller opaque shadow cores sit under surface-selected, shared alpha-cutout twig/leaf sprays. Fine bark twigs anchor those sprays; geometry is concentrated on visible outer surfaces instead of hidden interiors
- Existing terrain scan textures provide small-scale tonal/normal variation for the distant canopy cores. This is a material proxy under the leaf cards, not scanned-foliage imagery. All texture files already exist in the project
- Adds jointed ashlar courses, projecting string courses, tower arrow slits and collars, a true masonry gate arch, two small gate lanterns, occasional woven banners, eave fascia, ridge caps and chimney pots
- Replaces precisely the two-triangle luminous rectangle over the distant gate. Other windows and all near-world lighting are retained
- Gives islands interrupted exposed cliff sections, pale strata, talus ribs and broken foam lines. The additions join below sea level and do not introduce floating land or a second overlapping water plane
- No collision, safety, G0 or shop geometry is edited

## Isolated build results

With the isolated seed-12040 base geometry:

- 252,315 net added triangles across 56 detail material batches
- 1,762 detailed crowns; 47,218 cutout leaf sprays and 5,289 fine twig segments
- 174 nearby giant-tree crown components receive 16,117 of those sprays, with sampling that covers both deck-height and high telecom viewpoints
- 1,305 ashlar blocks; 137 detailed roofs; two old gate-light triangles replaced
- 628 coastal cliff triangles, 348 stratum strips and 232 broken foam segments
- 11 new material definitions, zero new texture files

The integrated build's returned counts are authoritative. This pass stays under the requested approximately 300k added-triangle budget. Cutout foliage still adds alpha-test cost; actual Windows/VRChat frame time and compressed download size require runtime profiling and a real build.

## Checks and limits

- All generated positions and UVs are finite; triangle indices are valid; no zero-area faces were found
- New detail vertices remain outside the protected 35 m root-walk radius
- Isolated north/city/south/aerial Blender geometry previews were inspected and iterated. Initial sparse cards on pale opaque crowns were rejected in favour of darker textured cores and overlapping leaf surfaces
- These previews are not Unity/VRChat runtime captures

## Snow-boundary diagnosis

Ray checks against the actual forest-city and telecom cameras identify the alleged hovering ridge fragments as bare-rock material patches on continuous terrain. For example, telecom pixel (398,188) hits rock near source XYZ(-1974,1948,323), while the apparent gap beneath at (390,202) hits a nearer snow-covered slope at (-1773,1728,276). The upper-right sliver is the same rock patch seen in the forest-city view, near (-392,1936,327).

The original high-frequency height-dependent snow boundary can leave higher distant rock exposed behind lower foreground snow. The near-match between snow and sky colours makes this look detached. The approved stage-3 landscape patch smooths the snow boundary to 310 + 12 sin(0.003 x) + 5 cos(0.003 y), replacing the previous high-frequency 38 m / 24 m oscillations. The refreshed north preview no longer shows the isolated dark wedge. No valid terrain was removed and no fog was used to conceal it. Snow/sky contrast is a separate lighting/material adjustment.
