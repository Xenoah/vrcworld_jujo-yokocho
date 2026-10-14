# Shopfront lettering quality

The eight shop identities retain the same wording, fonts, crest source art, positions, UVs and 2048×2048 atlas dimensions. Only the 221 printed calls are rasterized at eight times their destination scale and BOX-filtered into the original atlas. The largest temporary print canvas is 8192×1024 RGBA, not a full 16384² texture. All 3,853,374 pixels outside print coverage are unchanged against regeneration of the pinned prior source.

This is authoring-time antialiasing, not extra runtime texture resolution or geometry. In the controlled authoring measurement, elapsed time increased from 5.998 to 8.555 seconds and peak resident memory from 71.5 to 145.5 MiB. These measurements are not Unity or VRChat performance estimates.

The editable GLB now embeds this one atlas as lossless PNG. Thirty other images and unrelated geometry remain protected by the exporter tests. The lossless image adds approximately 4.065 MB to the GLB compared with its JPEG alternative. Unity already used the original PNG input; this GLB encoding improvement must not be represented as a separate Unity runtime texture upgrade.

The compact test fixture regenerates the old atlas from pinned source and fonts, checks its literal SHA-256, and then compares every protected pixel. A redundant 4.18 MB copy of the old image is not shipped. Missing or different fonts fail clearly rather than silently substituting a platform font.

- [Current print tests](shopfront_print_validation.json)
- [Current selective-lossless exporter tests](shopfront_lossless_validation.json)

Controlled Blender comparisons use the actual model with matching cameras, exposure, sample count and guide-aware denoising. They are not Unity runtime captures. Geometry/collision preservation is established separately by native payload contracts, not inferred from pictures.
