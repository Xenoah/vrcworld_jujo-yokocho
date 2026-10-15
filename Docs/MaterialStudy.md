# Original seamless PBR materials, v2.20 source preview

This document describes the material source, calibration and production-stage
evidence. Final adoption is recorded in `Docs/ORIGINAL_PBR_REVIEW.json` against
the exact origin hash. Numerical validation is not art admission or runtime QA.

## Origin and repeatability

The generator `Source/author_seamless_pbr.py` constructs new mathematical fields
from explicit, recorded random seeds. It reads no photographs, scans, existing
texture pixels, downloaded assets, or model-generated bitmaps. Old scans are used
only in separately labelled visual comparisons. The new material pigments are
manually authored, not measured or matched from old source pixels. All four maps
of a family share the same original latent fields; no albedo-to-height inference
is used. These are artistic physically based material maps, not measured scans.

The four families are aged fibrous bark, silver-weathered structural timber,
fine oiled counter timber, and moss-covered weathered mineral rock. Development
revisions are excluded from the public roster. No AI-generated image is used.

## Encoded maps and physical scale

- Albedo: RGB 8-bit PNG, 2048 by 2048, sRGB pigment only.
- OpenGL tangent normal: RGB 8-bit PNG, 1024 by 1024, linear, +Y.
- ARM: RGB 8-bit PNG, 1024 by 1024, linear R=AO, G=roughness, B=0.
- Height: grayscale 16-bit PNG, 1024 by 1024, linear.

The three data maps use exact 2 by 2 area reduction of 2048-square fields. Normal
vectors use wrapped central differences of the same height and a metre-valued
height scale. Height is not applied to mesh vertices or silhouettes. Albedo has
intrinsic pigment layering but no directional lighting or baked occlusion.

Dominant tile scale: bark 2.78 m, structural timber 1.538 m, counter timber
1.333 m, mineral rock 1.538 m. Secondary materials intentionally use other
existing scales; one map cannot represent the same exact physical grain size
across every old material. No UV scale or transform is altered to hide this.
The paired map generator reports exact effective relief spans and normal bounds.

Bark uses broad interrupted longitudinal cortex, narrower fibrous clefts, sparse
transverse scission, small cortex aggregates, and restrained lichen pigment.
Timber has variable-width growth bands, grain deflected around small knots,
pores and restrained checks. It contains no construction seams, nails or baked
board edges. Rock uses multiscale granular fracture relief, small mineral
laminae, quartz and muted iron-oxide pigment, not large baked rubble silhouettes.

## Bounded additive integration

Final map paths are under `Assets/TreeTopYokochoOriginalPbr/Textures/PBR`.
Core 2.19 source, GLB, native meshes, collision, manifest, historical textures,
metadata and runtime code remain unchanged. The material generator alone writes
source maps and evidence; it does not build or modify a Unity scene. In the
integrated source-preview package, `Tools/TreeTop Yokocho/0 - Build or Complete
Preview` runs the core builder when needed, then installs the original-PBR and
entry-system overlays. Its preflight checks the reviewed source and map hashes.
The PBR installer clones targeted materials into the overlay-owned generated
directory and rebinds only the matching original renderer slots. The historical
core assets and baseline build remain separate from this additive integration.

`Docs/material_slot_mapping.json` enumerates all 31 affected material names and
existing slots. Texture-only materials stay texture-only. Material tints,
roughness multipliers, normal strength, UV transforms, emission and every
non-target material/property remain unchanged. Geometry, vertex colors,
colliders, navigation, stations, signs and lighting are outside the scope.
The exact old-to-new descriptor mapping is also provided as the unchanged
reference helper `Source/authored_pbr_materials.py`. The integrated menu applies
the reviewed overlay plan, rather than rewriting the core manifest or generator.

Calibrate only the ten original nonzero 0.014 parallax values: bark 0.008,
weathered timber 0.0018, counter timber 0.0006, mineral rock 0.006. Preserve every
explicit zero and absent slot. This is conservative shader UV parallax
calibration, not a claim that Unity parallax amplitude equals metre relief.
No new textures, generated materials or import metadata may overwrite the core.

## Evidence and limits

Numerical verification independently decodes the PNGs and checks actual hashes,
channel/depth/dimension bounds, exactly zero metal, roughness bounds, forward
unit normals, +Y direction, height/normal agreement, periodic function identity
and ordinary wrap-step versus interior-step statistics. A seam is an ordinary
one-pixel sample interval, not a requirement for duplicated edge pixels.
Numerical success is not proof of visual realism or material acceptance.

Proof render scripts import the immutable original GLB or use an explicitly
labelled studio object. Only map images are replaced in actual-model proofs.
No new geometry/UVs, remeshing, displaced silhouettes, changed material tints,
lighting fixes, or image-model repainting is used to make the candidate look
better. Full-world comparisons use the original scene lighting, cameras and
display settings. Isolated trunk and rock proofs use the same neutral lights
before and after. Studio cylinders and planes are test primitives and do not
claim correct endgrain. Actual timber also uses the original bevelled member
construction and UV function. Existing geometry lacks separate endgrain mapping.

Every final proof JSON records the exact textures or baseline geometry hashes,
camera and render settings. Full-world previews additionally offer a labelled Intel Open Image Denoise
color-only pass, using the unchanged baseline denoiser; original raw renders
and their hashes are retained in each world proof directory. No new scene
content is synthesized. These
are not Unity/VRChat runtime captures. Unity shader, importer compression,
parallax, mipmaps, lighting, memory and performance still need actual Unity
validation. The original old maps remain historical/core scans and are never
relabelled original. Broad color or surface character differences must be
reviewed in the unchanged world context, including secondary uses on scenery.

## Final comparison selection

The selected material set combines the final longitudinal-lamina bark,
low-contrast moss-covered mineral rock and the two timber families. The final bark has long irregular-width cortex
ribbons, independently interrupted clefts, torn lamina shoulders and three local
branch-scar flow regions. The albedo and normal/height silhouettes share those
fields. Cavity AO is restrained without changing the final albedo, normal or
height anatomy. The art goal is recognizable, quietly repeating procedural
bark at the actual giant-tree scale, not equality with scanned bark microdetail.

The first gray rock was unsuitable for the old family's shared terrain and
forest-canopy slots: it made the distant landscape conspicuously gray and busy.
The selected moss-covered mineral rock uses restrained olive pigments and
low-contrast stone/moss transitions. No old material tint or scene light was
changed to compensate. This shared family remains an artistic compromise across
rock, terrain and canopy roles. Inspect the complete unchanged world, not just
the studio specimen.

Final adoption and its reviewed origin hash are recorded in
`Docs/ORIGINAL_PBR_REVIEW.json` after the matched near/mid, grazing-light,
2 by 2 and full-world comparisons. No numerical PASS implicitly grants it.
Development revisions and work logs are excluded from the public roster.
