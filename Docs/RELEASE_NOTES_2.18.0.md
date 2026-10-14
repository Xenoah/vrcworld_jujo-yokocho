# v2.18.0 — Framed moonlit tea pendants

This is a narrowly scoped continuation of the verified v2.17 RPG names, licensed typography and venue-specific lighting. It is an unpublished Unity production-source candidate, not a compiled or uploaded VRChat world.

## Visible refinement

The two existing 月詠みの茶房 pendants keep their washi-like luminous bodies, suspension positions, light colors and two existing baked point-light records. Their four chamfered timber caps now use the existing dark timber material. Twelve sparse solid vertical stiles frame the diffusers, avoiding the previous unframed fluorescent-box impression without adding ornate effects or changing authored light color/intensity settings (geometry can still affect shadows).

No new material, texture, shader, point light, animated effect or transparent layer is introduced. The complete fixture envelope is unchanged. All chairs, tables, counters, signs, stations, exits, routes, collisions and other seven venues are preserved.

## Measured source cost and scope

The generated export has 1,107 source mesh batches, 2,692,591 vertices and 2,296,997 triangles: +1 batch, +288 vertices and +144 triangles versus v2.17. Four cap meshes retain their positions, topology, native UVs and vertex colors. Their exported GLB UV scale follows the unchanged existing DarkTimber descriptor (0.65), replacing the former PaleJoinery scale (0.7). The twelve added stiles account for all new triangles and fit within the old cap envelope.

Compared with the initial verified v2.14 world, the combined source is smaller by 507,679 vertices and 352,610 triangles, while its source mesh batch count is higher by 49. Source batch count is not a measured draw-call count. No FPS, runtime memory or Unity download-size benefit is inferred from these figures.

## Versioned evidence

The v2.17 source ZIP and its frozen RPG oracle remain unchanged. The pendant revision requires a separate exact admission gate and a test-only inverse that restores the complete v2.17 native payload before historical regression tests. A source-local feature toggle is not advertised as a substitute for the verified rollback archive.

The before/after S05 preview uses the same actual-model camera, source lighting, exposure, sample count and guide-aware processing. Other seven gallery frames remain explicitly labeled v2.17 because their source appearance is unchanged. Raw PNG and EXR intermediates are retained as execution evidence but omitted from the bounded source ZIP; selected processed previews and provenance sidecars are included.

The accompanying validation record, rather than this release note alone, establishes whether all source and clean-extraction checks passed. Unity compilation, lightmap/probe baking, headset stereo, avatar calibration, FPS and final world download size remain untested.
