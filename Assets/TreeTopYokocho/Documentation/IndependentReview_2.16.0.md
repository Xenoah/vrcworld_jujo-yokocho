# Independent source review — v2.16

Reviewed artifact: native `f52f44353420638bb500afd37f04b9c55d7f30ab4da4c369ad4b4c98080e3c46`, GLB `65fdc1ce1da77db04ceae244ae2089852756705dd89f60e735b177336b6a0b15`.

- Exact 815 nonshop payloads and 40 retained root components: PASS.
- GLB arrays/materials and unique, complete identity scene placement: PASS.
- Final actual-geometry access: 208 required probes PASS; 49 exits connected.
- All eight new material names and additive routing: PASS; prior routing unchanged.
- 198 asset meta GUIDs: unique at review time, before any documentation-only additions.
- Frozen oracle `6b039bba23205bf89c1d92bd391469b162f50c8775697e19389d142289a6ce9d`: exact 291 shop rows, 815 complement, 46 manifest-field hashes and eight dependencies independently matched.

No Unity compilation, bake, avatar IK, VRChat or headset execution was available. Component review does not replace the full regression and clean package extraction recorded separately.

Fresh source generation independently reproduced the final native, collision, GLB, manifest and both sign atlases byte-for-byte. Both new atlases were also generated into an empty directory with the installed Japanese fonts, ruling out baked-atlas fallback for that proof. See [reproduction record](shop_source_reproduction.json).
