# RPG shop identities, study 2

Source typography and deterministic authoring evidence for the integrated RPG identity revision.
`rpg-identity-handoff-manifest.json` enumerates authoritative files and SHA-256 hashes.
`rpg-identity-hooks.patch` records the narrow food/night module hooks and pinned legacy-atlas fallback update. The supplied project also contains the versioned dispatcher and manifest integration.

## Names and type

- S01 竜の熾火亭 — Noto Serif CJK JP Bold
- S02 風渡りの麺工房 — Klee One SemiBold
- S03 旅人の燈火亭 — Noto Serif CJK JP Bold
- S04 宵闇の魔女 — Noto Serif CJK JP Regular
- S05 月詠みの茶房 — Noto Serif CJK JP Regular
- S06 星屑の蒸留所 — Kaisei Decol Medium
- S07 吟遊詩人の隠れ家 — Noto Serif CJK JP Bold
- S08 妖精の菓子工房 — Klee One Regular

Bundled renamed subsets retain original glyph outlines. OFL license/copyright files and original metadata are included. No runtime font dependency. `fonttools==4.61.1` is required only for glyph tests and optional font maintenance.

## Integration and scope

Pass literal `rpg_identity=True` to both venue `bake_textures` and `build_venue` functions. Defaults remain false. Identity mode restores a pinned original atlas before each deterministic overwrite, so repeated/toggled runs cannot inherit stale pixels. Disabling offline restores that pinned original rather than retaining a potentially RPG cached atlas.

Only eight sign UV batches change. Materials, vertices, faces, batch order, seats, collision metadata, routes, lights, steam, RNG behavior, and other geometry are unchanged in the venue comparisons. Food subtitles/emblems and specified nightlife secondary regions are owned atlas edits; pixels outside those rectangles remain exact. Existing menu typography is not redesigned.

Build metadata wiring is included in the integrated project. Unity/VRChat runtime checks remain unperformed. VenueLighting.md documents the separate lighting source revision. The sign-mesh proofs use explicit neutral albedo emission inspection, not the final lighting look.

## Reproduce checks

From checkout root, using the repository Python environment with requirements installed:

    python Source/test_rpg_shop_identities.py
    python Source/test_food_venues.py
    python Source/test_nightlife_venues.py
    python Source/prepare_rpg_sign_model_proofs.py
    python Source/audit_rpg_physical_aspect.py
    blender --background --python Source/render_rpg_sign_proofs.py

Fresh result: 7 identity tests, 7 food tests, and 14 nightlife tests passed. Proof regeneration matches the existing rendered GLB SHA exactly. All eight titles have zero clipped ink pixels. Actual production triangle Jacobian tests measure world-to-texel anisotropy independently of the configured aspect constants: maximum 1.0016183 (0.162% integer-raster rounding); S05 1.0002561. Text is fit by point size and tracking, not width stretching. Title ink stays inside the sign silhouettes/margins.

Evidence: Preview/rpg-sign-model-proofs/proof.json, physical-aspect-audit.json, renders.json, and eight-actual-model-signs.png. The portable test commands above reproduce the source checks.

## Font maintenance

Normal builds use bundled hash-checked subset fonts. Optional subset regeneration runs `build_rpg_fonts.py` then `build_rpg_display_fonts.py`; it admits only fontTools 4.61.1 and pinned source hashes. Display font upstream sources/licenses are bundled and checked. Noto full TTC sources are not bundled: maintenance expects the exact installed files/hashes named by rpg-fonts.json; missing or differing Noto is a hard failure, never a silent substitution. The two scripts were run in an isolated copied directory and reproduced the fonts, licenses, and manifest byte-for-byte. Evidence: Preview/rpg-font-reproduction/report.json. This is not a claim that every clean machine already has those Noto upstream files.
