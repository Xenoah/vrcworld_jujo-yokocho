# Selected fantasy shader implementation

## Verification status

Selected after actual-model Blender comparisons: `warped_soft` sea + `teal_readable` sky. This is not Unity/VRChat runtime validation. Unity 2022.3.22f1 import, generated surface-shader compile, bake, stereo and GPU/frame-time measurements remain required.

- 21 source/numeric/native-use tests pass, with `YOKOCHO_ASSET_ROOT` pointing at the actual project. No skipped test in that run.
- Blender 4.3.2 node-construction smoke passes, including Glaze reporting and sky strength=2 applied once.
- Independent read-only review checked the wave chain rule, inverse normal rotation, horizontal sea tangent reconstruction, periodic stars, bounds and meta guards; no concrete source blocker remained.
- Source-only tests cannot certify generated Unity variants, shadow/meta passes or VR comfort/performance.

## Art selection and actual use

Warm timber/ink/paper remain the foreground anchors. The sky adds stable sparse stars and a slow teal northern ribbon. The first low/faint sky and axis-aligned ruled-water trials were visually rejected, not called improvements merely because their parameters differed. Subsequent supported deck/nearest-sea/veranda views showed softer nonuniform water and a readable but restrained teal band.

Three genuinely different opaque shader families are added: Cloth, LanternPaper and Glaze. Shader assets increase7→10. No scene geometry, collider, navigation, transparent geometry, realtime light, particle or runtime script is added by this package.

The actual current cloth roster is ShopfrontTextile:8 batches/27,534 triangles, and CityWovenBanner:1 batch/15 triangles. Noren0–7 definitions currently have zero batches/triangles. Do not claim a GPU improvement from changing unused definitions.

ShopfrontTextile uses authored front/back geometry, reversed back winding, closed panel edges and double-sided rolled-entry sheets. Its `_Cull=2` restores the previous Surface/CullBack semantics; Noren definitions also retain Back if later used. Only the actual single-sheet CityWovenBanner uses CullOff. This is a culling-semantic restoration, not a measured FPS claim.

## Profile and editor routing

`Assets/TreeTopYokocho/Data/FantasyMaterials.json` is the selected array-based profile. Preserve manifest textures, tint, vertex colour, main texture scale, normal scale, emission, roughness and metallic. Apply only listed overrides after existing binds.

- Cloth and Glaze need `_YOKOCHO_NORMALMAP` / `_YOKOCHO_ARM` only when matching textures exist; never parallax for these shaders.
- Surface grain/patina reuses existing texture samples. Patina responds only to packed AO and therefore does not invent corrosion when no AO map exists.
- LanternPaper retains baseline emission and ink. Runtime breathing is ±1.2%, with20.27-second period. Meta pass bakes its steady base.
- Cloth and Glaze explicitly hold view-dependent specular terms at their base in UNITY_PASS_META. Zero emission alone would not guarantee a stable specular-workflow bake albedo.
- Glaze is opaque and nonemissive, with static view-dependent film tint bounded to ±10% F0 modulation. It is not glass refraction/transparency.
- SignAtlas, MenuAtlas, WarmWindow, TownLights, UtilityLampWarm and aviation safety beacons keep their previous shaders.

### Selected sky

Strength.15, direction-height.50, band falloff24, scene-linear colour(.045,.80,.46), drift.012rad/sec, direction(0,0,1) in Unity. Peak unoccluded additive RGB is bounded(.00675,.12,.069). Cloud attenuation, dusk palette/exposure and sky strength are preserved. Height and falloff shader controls are clamped to.15–.65 and16–60. The local fantasy keyword removes both stars and aurora when disabled.

Star cell identity and longitudinal derivatives wrap periodically. Filter support remains within the cell; high polar regions fade out. Stars have no time-dependent seed or blinking.

### Selected sea

`_RippleScale=.035`, `_RippleStrength=.18`, `_WaveSlope=.010`. Two oblique waves use slow transverse phase warps with exact chain-rule gradients. The second existing normal-image sample rotates, and its decoded xy rotates back with the transpose. Three texture samples remain, zero vertex displacement remains. Maximum analytic long-wave vector slope is below1.012×the parameter.

Baseline vertex displacement was bounded±.043m. Removing it changes vertical silhouette from the old animated position by at most.043m; this is deliberately not called exact animated parity. The mesh optimizer owns nearest-supported-view projection evidence and unchanged boundary/domain tests. New shader waves do not move vertices, so sea topology reduction does not alter their phase or silhouette.

Water assumes horizontal world-up sea, not waterfalls. WorldNormalVector supplies the imported tangent basis; dot products project the world ripple normal into that frame. Revised UVs, mirrored tangent handedness and sector boundaries do not set wave direction.

## Costs and quality choices

No extra texture fetch for Surface craft. Cloth and Glaze use one albedo plus optional normal/ARM. LanternPaper uses one albedo. Sky adds ALU but no texture/noise-octave/scene-shell; Water retains three fetches with extra phase/gradient ALU. Surface shaders generate lighting/shadow/meta passes: no handwritten extra pass is not the same as one draw call.

Low tier can disable fantasy/craft keywords and set weave, film, breathing or long-wave amplitudes tozero. Numeric zero is not a guarantee of ALU stripping. Existing cloud/foliage/steam/beacon shaders remain unchanged. No FPS/compiled variant-count claim is made.

## Blender helper and limits

`Source/fantasy_preview.py` applies selected world-wave phases and two source normal-image samples, but not the Unity fwidth fade. Cloth uses Principled sheen and omits unfiltered weave. Glaze maps film colour into existing Principled Specular Tint, preserving base/metal/roughness, but its BSDF/F0 mapping and geometric normal differ. Lantern uses a fixed supplied time snapshot. The separate Source/surface_craft_preview.py pass approximates the bounded Surface roughness/metallic formulas from existing imported samples, without additional image nodes. It preserves base, normal and emission links, refuses unexpected graphs, and reports differences in tint quantization, parallax, texture filtering and BSDF. Current positive-patina metal controls have no ARM binding and therefore produce zero patina; no replacement grime mask is invented.

Sky helper inserts aurora into existing Background Color, so the existing Strength scales original plus addition exactly once. Diffuse ambient is independent. Stars are omitted rather than falsely reproducing the runtime derivative filter. Procedural hash precision, tone mapping and reflection handling differ between renderers. Dynamic runtime sky does not imply continuously refreshed baked probes.

## Required Unity acceptance

Import and inspect every shader/variant; verify cloth front/back and shadow/meta; bake paper/cloth/glaze; inspect signs, atlases and normal-map import/handedness; compare sea seams/shoreline/nearest view; inspect both eyes and star mip footprint; review aurora in Linear colour space and probes; measure frame events, variants, opaque GPU time and existing cloud/steam overdraw on target VR hardware.

References: Unity Surface Shader documentation https://docs.unity3d.com/ja/2022.3/Manual/SL-SurfaceShaderLighting.html and instancing macros https://docs.unity.cn/2021.1/Documentation/Manual/SinglePassInstancing.html. Documentation does not certify compilation.

## Atlas-specific cloth scale

ShopfrontTextile alone uses 4,096 procedural cycles per UV repeat: the measured area-weighted U/V periods are approximately 2.533/2.157 mm. Unused Noren definitions and the distant CityWovenBanner retain 96. Existing derivative filtering fades the normal detail at roughly 5 to 2 pixels per period; visible threads at ordinary viewing distance and zero stereo shimmer are not guaranteed. Blender omits this weave. See [measured atlas correction](ClothAtlasWeave.md).


## v2.16 shop replacement scope

The individually designed shops supersede the prior repeated shop shell and 107 historical noren slices. Those older invariants remain historical inverse tests, not descriptions of current shop geometry. Current admission uses the exact 291-row v2.16 oracle and actual clearance checks. Nonshop shader/geometry preservation remains separately enforced. See [ShopPersonalityDesign](ShopPersonalityDesign.md).
