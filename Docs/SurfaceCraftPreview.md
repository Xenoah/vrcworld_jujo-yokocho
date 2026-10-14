# Optional Surface-craft Blender formula diagnostic

This does not modify Unity shaders or the accepted fantasy helper. Import `configure_surface_craft` from `surface_craft_preview.py`, then call:

`report = configure_surface_craft(bpy, fantasy_profile, manifest['materials'])`

Call once after imported material setup and before fog wrapping. Include `report` in preview sidecars. It can accompany the existing fantasy helper; Surface omission in that earlier helper must not be mistaken for this independent pass's applied report.

The exact bounded shader modulation is represented using existing Blender scalar/material signals:

- Reuse existing base image RGB and imported pre-vertex colour factor for grain. Never use vertex tint/AO as grain.
- Reuse packed image red for AO only when the manifest actually has an ARM map.
- `S' = saturate(1 - saturate(R) + (grain-.5)*G - .25*patina)`; `R'=1-S'`.
- `M'=saturate(M)*(1-patina)`.
- Preserve original roughness/metallic input chains as inputs to the added math. Preserve BaseColor, Normal and Emission links/values entirely.
- Do not create new image nodes, load new images or introduce new sampling coordinates. Refuse unexpected graph structures rather than guessing. Repeat calls are idempotent.

Actual frozen GLB smoke test applied25 materials, addedzero image nodes, preserved every protected material socket and did not duplicate modulation on a second call. Four scalar formula tests pass. No actual-frame comparison has yet been performed for this helper.

Caveats: imported tint factors are glTF-quantized, not identical to Unity manifest floats; parallax is not emulated; source texture decode/compression/mip filtering and Blender Principled BRDF differ. This is a source-formula approximation, not runtime parity or a decorative preview-only effect.

Run actual graph guard with:
`blender --background --factory-startup --python blender_surface_craft_smoke.py -- --asset-root /path/to/project`

Run scalar tests with:
`python -m unittest discover -s SurfacePreview -p 'test_*.py' -v`

Final report additionally distinguishes nonzero grain controls, nonzero patina controls and material bindings that actually permit nonzero patina. Current25 applied materials have25 nonzero grain controls,5 nonzero patina controls butzero ARM-backed active patina terms. A nonzero control also does not prove nonzero output after clamping or a visible difference. No fallback grime/AO mask is invented to make unused knobs visible. Unexpected nonwhite materials missing an explicit imported colour factor are now omitted instead of silently using white.
