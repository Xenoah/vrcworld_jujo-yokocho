# Production-stage visual assessment

制作段階の評価。最終採否は `Docs/ORIGINAL_PBR_REVIEW.json` 参照。

This is the authoring-stage assessment. The final admission decision is recorded
separately in `Docs/ORIGINAL_PBR_REVIEW.json`, bound to the exact origin hash.

Comparison views preserve the original geometry, UVs, material IDs, colors and
world lighting. No baseline or historical texture is relabelled as original.

- Bark: r8b preserves r8's explicit longitudinal fissures and harder cortex
  shoulders. Compared with the original scanned bark, it remains simpler and
  less photographically rich, but reads as bark rather than porous mud/rock.
  Mid-distance repeats are quieter than the scanned map's large recurring knots.
  Normal and albedo belong to the same authored shape fields. AO is restrained.
- Weathered timber: restrained silver-gray growth bands, grain and small knots
  fit the existing deck and structural member UVs. Construction joints come
  from the unchanged geometry, not from baked seams in the maps.
- Counter timber: smaller grain, shallow pores and lower roughness remain matte
  enough to avoid a plastic sheen in the original counter lighting. Its hue is
  original, not a pixel-derived match to the old photograph.
- Mineral rock: the gray first study changed distant terrain/canopy character
  too much. The final low-contrast olive moss/stone study restores a subdued
  dark-green landscape character under the unchanged world lighting. It is a
  shared-role compromise and requires full-world review.

Remaining limits: no scan-equivalence claim; generic primitive endcaps are not
endgrain; relief does not change silhouettes; secondary UV scales differ from
the dominant physical calibration. Blender previews are not Unity import,
compression, shader, parallax, mipmap, performance or VRChat runtime validation.

Final art admission must be read from `Docs/ORIGINAL_PBR_REVIEW.json`.
This authoring-stage assessment does not itself grant admission. Numerical seam checks alone cannot approve visual continuity
or realism. The final proof roster, not the development Studies directory, is
the authoritative set for that review.
