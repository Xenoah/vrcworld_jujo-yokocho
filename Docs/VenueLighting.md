# Venue-specific static lighting, v2.17

This authoring revision gives each of the eight venues a distinct palette using its existing fixtures. It does not add real-time lights, animated colors, flashing effects, or runtime controls.

## Exact scope

- All 374 point-light records remain: 15 venue-owned records and 359 unchanged exterior, stage, and circulation lights.
- The 15 positions, ranges, and base strength values are unchanged. Their explicit color and intensityMultiplier change the effective Unity intensity; unchanged base strength does not mean unchanged output.
- Twelve exact owned visible-fixture batches are assigned cloned materials. This adds twelve named material assets without adding source mesh batches; actual runtime batching and material cost have not been measured. Their vertices, indices, UVs, authored colors, bounds, and insertion order remain unchanged. Existing material descriptors are retained.
- The snack has one existing point light, not a separate neutral fill. Its Ceramic ceiling shade alone receives a low static plum emission of 0.16. The cocktail venue’s rear accent point has no separately authored visible diffuser.
- Shared diffuser batches use the average of explicitly associated fixture colors. No location heuristic recolors unrelated geometry.

## Palette and source budget

### S01 — Ember charcoal with neutral-gold task light
- S01_F01 (task): RGB [1, 0.86, 0.7], effective intensity multiplier 0.82.
- S01_F02 (accent): RGB [1, 0.38, 0.12], effective intensity multiplier 1.0.

### S02 — Mint-white ramen workshop
- S02_F01 (task): RGB [0.86, 1, 0.96], effective intensity multiplier 0.72.
- S02_F02 (task): RGB [0.86, 1, 0.96], effective intensity multiplier 0.72.

### S03 — Amber hearth with readable food key
- S03_F01 (task): RGB [1, 0.86, 0.72], effective intensity multiplier 0.78.
- S03_F02 (accent): RGB [1, 0.47, 0.2], effective intensity multiplier 0.9.

### S04 — Pearl-lavender retro snack and subdued plum shades
- S04_F01 (key): RGB [1, 0.75, 0.96], effective intensity multiplier 0.79.

### S05 — Moon-jade tea with cool clerestory
- S05_F01 (key): RGB [0.76, 0.9, 1], effective intensity multiplier 0.77.
- S05_F02 (task): RGB [0.9, 1, 0.91], effective intensity multiplier 0.73.

### S06 — Cyan-white cocktails and teal backbar
- S06_F01 (key): RGB [0.86, 1, 0.95], effective intensity multiplier 0.73.
- S06_F02 (accent): RGB [0.22, 1, 0.78], effective intensity multiplier 1.0.

### S07 — Indigo listening room with neutral front key
- S07_F01 (accent): RGB [0.39, 0.48, 1], effective intensity multiplier 1.05.
- S07_F02 (key): RGB [0.92, 0.93, 1], effective intensity multiplier 0.74.

### S08 — Ivory rose-white confectioner
- S08_F01 (task): RGB [1, 0.94, 0.86], effective intensity multiplier 0.72.
- S08_F02 (task): RGB [1, 0.9, 0.86], effective intensity multiplier 0.74.

## Runtime and preview validation limits

The Unity editor preflights the profile, exact fixture roster, cloned material descriptors, shader presence, and required paper properties before scene or generated-asset mutation. Points retain LightmapBakeType.Baked and the prior soft baked-shadow policy. This is source validation, not Unity compilation or a completed bake.

The Blender comparison uses the same authored numeric RGB and relative multiplier, but uses live Cycles point energy strength × 110 rather than Unity baked intensity strength × 1.65. Emissive surfaces are camera-visible only in the preview, while Unity can use emission in its bake/probes. BRDF, color management, reflections, indirect illumination, and light units differ. These images cannot certify actual Unity brightness, face color, glare, or VR comfort.

RGB-weighted intensity and mesh-area emission budgets, and the sampled seated-face point-light proxy, are conservative authoring diagnostics. They are not lux, spectral CRI, perceptual exposure, or physical lighting measurements. Current actual-payload evidence is in venue_lighting_actual_audit.json; it must be regenerated when the manifest changes.

No Unity shader/C# compilation, lightmap/probe bake, headset stereo, on-device performance, or upload was performed.
