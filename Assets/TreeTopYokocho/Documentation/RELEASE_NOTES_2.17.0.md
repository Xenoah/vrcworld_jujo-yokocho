# v2.17.0 — RPG shop identities and venue lighting

This local source candidate follows the verified v2.16 eight-venue redesign. It has not been published, compiled in Unity, baked, uploaded to VRChat, or tested in a headset.

## Eight complete identities

- S01: 竜の熾火亭, charcoal grill.
- S02: 風渡りの麺工房, noodle workshop.
- S03: 旅人の燈火亭, oden and broth.
- S04: 宵闇の魔女, retro snack/lounge.
- S05: 月詠みの茶房, seated tea salon.
- S06: 星屑の蒸留所, cocktail and whisky bar.
- S07: 吟遊詩人の隠れ家, listening/music bar.
- S08: 妖精の菓子工房, confectionery and gifts.

The three nightlife venues remain three of eight, 37.5%, rather than exactly 30%. Each retains its different architecture, counters, furniture, circulation and interior authored in v2.16.

## Typography

Main and secondary sign artwork uses licensed, bundled Japanese CJK fonts. Noto serif treatments, Klee One-derived merchant/storybook faces and Kaisei Decol-derived engraved lettering are differentiated by venue. Fonts are authoring inputs outside Assets, not runtime text dependencies. The bundled upstream maintenance fonts add approximately 21 MiB to uncompressed source authoring files; that is not measured Unity build/download size. Subset fonts have their own renamed families and include OFL notices and pinned official upstream provenance.

Titles fit through point size, tracking and aspect-correct UV windows, never anisotropic font stretching. Eight exact sign UV batches change; physical sign vertices and faces do not. All eight actual-mesh title masks have zero clipped ink pixels in the source proof. The cocktail portrait sign uses the full vertical name, and its obsolete secondary menu heading is replaced.

## Lighting

Existing 15 venue point lights receive explicitly authored colors and bounded effective intensity multipliers. Warm charcoal and oden, mint-white noodles, pearl-lavender snack, moon-jade tea, cyan/teal cocktails, indigo music and ivory/rose confectionery share the same overall world atmosphere without forcing all interiors amber.

There are no added point lights, realtime-light count increases, animated color cycles or strobes. The 359 unrelated circulation, stage and exterior point lights are unchanged. Twelve exact visible fixture batches use bounded material clones. This adds twelve named material assets but no mesh batches; runtime batching and material cost are unmeasured. The snack still has only one existing point light, with a separate low-emission plum ceiling shade rather than an invented additional fill light.

## Preservation and honest limits

The candidate retains 1,106 source mesh batches, 2,692,303 vertices, 2,296,853 triangles and 49 station IDs. Mesh positions, faces, authored colors, normal inputs, collision, seats, exits, routes and safety structures are unchanged from v2.16. Only reviewed sign UVs, named fixture material bindings, the two venue atlases and explicit identity/light metadata change. The additional source batch count relative to v2.14 remains +48; source batches are not measured draw calls.

Blender images show the actual generated model, not AI-painted mockups or Unity runtime. Cycles uses live point lights, camera-only emission, a different BRDF and different light units. Runtime C#/shader compilation, lightmap/probe baking, reflection behavior, headset stereo, avatar calibration, performance and final upload remain untested. Source checks do not establish FPS or Unity build size.

The exact revision gate, clean-extract regression and final archive checksum must be recorded after art review; this document alone is not an acceptance record.
