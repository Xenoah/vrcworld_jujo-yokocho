# Existing foliage emission preview fidelity

This is a Blender approximation of an existing runtime term, not a new runtime foliage effect. Runtime Foliage and Cloth shaders, profile, material descriptors and geometry are unchanged.

The actual Foliage shader computes `c = texture.rgb * materialTint.rgb * vertexTint.rgb` and `Emission = c * .035`. Its GLB descriptors carry zero emission. The helper reuses the imported Principled Base Color socket, already including image/tint/vertex tint, to provide that existing radiance on camera rays only. No additional texture node, sample coordinates, alpha, normal, ARM, roughness or metallic changes are made. Two arithmetic/ray nodes per admitted material are added. Existing emission or unsupported graphs are preserved and explicitly omitted.

## Integration

Copy Source/foliage_preview.py. Apply renderer.patch to the exact v2.16 renderer or copy supplied full Source/render_preview.py after verifying its baseline. The hook is unconditional, because this emission belongs to the existing Foliage shader rather than the optional fantasy profile. It runs after the existing general camera-emission gate and before atmosphere fog; no double gate or fog bypass. Its report and helper SHA are included in each sidecar. Keep both arms of crown atlas A/B on this same helper/renderer version so the emission correction does not masquerade as an atlas improvement.

Copy portable Tests files into project Tests. Run `python Tests/test_foliage_preview_hook.py`. Run `blender -b -t 1 --python Tests/test_foliage_preview_blender.py -- --project-root . --report Docs/foliage_preview_smoke.json` for the actual GLB admission check. Neither test renders a frame.

## Verified v2.16 evidence

Actual GLB SHA65fdc1ce1da77db04ceae244ae2089852756705dd89f60e735b177336b6a0b15, Blender4.3.2. Eight materials admitted: Foliage0–3, FoliageSpray, FoliageScenerySpray0–2. ForestSpray is manifest-only and explicitly omitted. Tests preserve every original non-emission node input/link, all nonselected graphs, alpha, zero extra image nodes, exact .035 camera gate and idempotence. Negative absent/no-node/existing-emission fixtures are reported and preserved. The two renderer insertion/source-constant tests pass.

No emissive indirect or reflection contribution is added in this preview. Wind, exact Built-in backface TBN, normal decode/compression/mips, Unity BRDF, stereo, bake and performance remain unverified. Imported tint is quantized. This does not establish runtime parity or justify changing existing Mirror-style backface normals.
