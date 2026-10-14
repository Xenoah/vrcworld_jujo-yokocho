# Counter hotspot source diagnostic

Controlled source: combined v2.15 GLB SHA c3e3606229b7b2bc90b8f3b9dad128033575b6609a44b47c3c7851de1823d3c3, fantasy profile SHA 6cf7669a43f2b45678057f22fcf344cc753b9b65b350e0c6b13700e3131f3c8e.
No runtime or profile changes proposed by this audit.

Counter uses wood_table_001 albedo/normal/ARM/height, tint (0.91,0.83,0.70), roughness multiplier 0.9, normal strength 1, UV scale 0.75, parallax 0.014, zero emission. Surface smoothness is `saturate(1 - ARM.g * roughness)`, not 1 minus the manifest scalar alone. Wood craft adds `(dot(linearAlbedo * tint, (.2126,.7152,.0722)) - .5) * .11` to smoothness. Counter patina is zero.

The source-image diagnostic decodes sRGB albedo after BOX reduction to the ARM resolution. It finds median roughness 0.2294 before craft and 0.2829 after craft. Craft roughens every sampled source texel, and reduces the source fraction below roughness 0.15 from 4.55% to 0.245%. This is not a screen-pixel statistic, headset test, mip simulation or light-response calculation.

In the frozen S01 Blender image, a compact near-white counter reflection exists beneath the lantern. The completed isolation trial below attributes that patch to live preview-lantern glossy contribution. Cycles preview lanterns are live point lights, energy strength * 110, radius 0.2, color (1,.48,.16). Unity builder lanterns are Baked points, intensity strength * 1.65, color (1,.52,.18), range * 1.25. Energy units are not interchangeable. The preview also makes emissive materials camera-ray-only, excluding emissive reflection/indirect illumination, while Unity uses its own bake and reflection probes. AgX versus Unity display mapping and shader BRDF add further differences. Therefore the bright patch cannot be attributed to equivalent runtime direct point specular.

An initial proposed control was to set only preview Lantern_* point-light `specular_factor` to zero. The empirical test below rejected that control because Cycles 4.3.2 ignored it. It was not used as evidence of successful reflection isolation. The completed diagnostic instead used verified Object.visible_glossy suppression, while leaving production materials and ordinary preview lighting unchanged.

## Empirical control verification (Blender 4.3.2 Cycles)

`test_cycles_light_factor.py`: Light.specular_factor 1 versus 0 produces identical synthetic renders. Do not use this ineffective control.

`test_cycles_glossy_visibility.py`: light Object.visible_glossy true versus false changes glossy reflection. In a direct-only test (max_bounces=0), the diffuse sphere half is byte-identical; glossy half peak decreases from 1.0 to 0.2549 in the fixed Standard-mapped PNG. These are test scene values, not world performance/lighting claims. An initial ordinary-bounce trial showed a small diffuse-half difference from changed indirect glossy paths. Therefore full-world diffuse illumination settings are preserved, but indirect diffuse pixels are not guaranteed identical.

`preview_light_isolation.py` contains the narrow verified diagnostic. Call after frozen preview Lantern_* point-light creation, record its returned report in the diagnostic sidecar, never enable by default. Preserve the ordinary bounce settings in the world trial; do not reuse the synthetic direct-only bounce override. No material, environment, geometry, camera, exposure, shader/profile or light energy changes. This suppression tests reflection attribution only and does not emulate Unity bake/probes.

## Completed S01 isolation

The controlled frame removes the central bright counter patch without any material changes. Exact matched settings and raw/denoised image hashes are in preview_light_comparison.json. In the declared counter ROI [510,460,610,500], raw display-luma mean changes 90.18 to 37.12 and P99 237.39 to 132.27 (0–255 units). These display-mapped measures are not scene radiance. No ROI pixel has all RGB channels over240 in either original or excluded raw/denoised image, so the visual description near-white does not establish channel clipping. S01_light_isolation.png labels the control explicitly. Keep production rendering/material unchanged; disclose live-point preview reflection limitation.

## Packaged preview evidence

The source archive includes selected processed PNG previews and their provenance sidecars. Raw PNG and EXR diagnostic intermediates are retained in execution evidence but omitted from the source ZIP to bound delivery size; the included renderer and guide-aware denoiser reproduce the workflow. Image provenance may reference those retained intermediates without implying that every raw file is bundled.
