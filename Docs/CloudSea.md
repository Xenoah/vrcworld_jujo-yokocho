# Elevated cloud sea / 雲海

## What was built

`Source/cloud_sea.py` adds 28 organic cloud banks below the raised alley. Source coordinates are X east, Y north, Z up. The v2.13 reviewed envelope is 93.2–124 m (actual exported geometry 93.816–123.604 m); L1 starts at 134 m, with higher decks at 140, 146 and 152 m. The cloud banks do not move any ground, shop, path, seat, collider, utility or tree.

- 36,288 triangles, 20,412 vertices, eight spatial mesh/material batches
- One shared `CloudSeaSilver` material, `TreeTopYokocho/CloudSea` shader
- Zero image textures, particles, runtime scripts, realtime lights or new colliders
- Nine rounded, independently varied billows per bank (252 total), rather than one large shallow plate or billboard-sheet stacks
- Real, irregular openings toward the northern road/city and southern sea/islands
- Peripheral openings allow the original forest and ground to remain visible
- Existing giant-tree crowns should extend well above 124 m; increase the landscape peer-tree heights separately, leaving their roots attached to the existing ground

The apparent volume comes from mesh relief, a lobed silhouette, procedural density, smooth edge fading and procedural normal shading. This is a deliberately inexpensive cloud illusion, **not** raymarched participating media. The ascent remains inside the actual central opening; it is not routed through cloud geometry. Clouds have no walkable surface.

## Build integration

The integration owner should make these changes in the existing files; the cloud module does not patch them itself.

1. In `build_world.py`, import `add_cloud_sea` from `cloud_sea`.
2. Call `cloud_sea = add_cloud_sea(g, M, rng)` after landscape generation and the existing-world altitude transformation, before `g.compact()`. Do not translate the cloud banks by the alley's +100 m offset.
3. Save the return value as `manifest['cloudSea']`. It contains only JSON-safe values and includes each bank, bounds, counts and viewing examples.
4. Do not add the cloud meshes to `c` or any collision payload.

The function restores `g.group`. It adds only its named cloud material and `Landscape/CloudSea_*` batches, and leaves all pre-existing geometry and materials unchanged. It consumes the supplied NumPy RNG for reproducible phases/heights, consistent with the existing generation API.

## Unity Built-in integration

The current material builder already uses `Shader.Find("TreeTopYokocho/" + m.shader)`. `shader='CloudSea'` therefore resolves the bundled shader without a special material-construction branch. Color is populated by the existing `_Color` path; the remaining authored properties have complete shader defaults. The additional cloud fields in the material JSON are descriptive; they are not required C# deserialization fields.

In `YokochoWorldBuilder.cs`:

- Recognize `TreeTopYokocho/CloudSea` as animated alongside Water/Foliage/Beacon
- Keep cloud renderers out of lightmap UV generation, static batching, baked GI and static occluders
- Turn cloud shadow casting and shadow receiving off
- Turn light and reflection probes off for clouds
- Preserve the eight spatial batches; do not combine them into one world-sized transparent renderer

The `Landscape/` prefix already disables shadow casting and lightmap generation in the present builder. The explicit cloud recognition prevents later refactors from accidentally treating the animated transparent banks as static occluders.

### Shader compatibility and cost

The shader is one vertex/fragment pass using `UnityCG.cginc`, shader model 3.0, Unity's fog variants and stereo-instancing initialization macros. It uses no URP/HDRP includes, geometry/tessellation shader, GrabPass, depth texture, camera script, compute shader or custom renderer feature. Alpha is premultiplied (`Blend One OneMinusSrcAlpha`) and fog is applied before premultiplication. It has no shadow caster pass.

Only three 2D value-noise octaves are evaluated per fragment. Analytic derivatives reuse those hashes for the apparent billow normals. An early outer-edge clip discards almost invisible pixels before noise work. Wind is a slow `_Time.y` world-space offset; mesh swell is limited to 0.15 m. The v2.13 generated mesh maximum is 123.604 m, so even the permitted maximum swell stays below 124 m.

The revised cloud-only triangle budget is 40,000; the generated 36,288 triangles stay below it. Small billows overlap locally to form continuous-looking clouds; this costs more transparent fragments than the original single-cap version. Transparent fill rate and overlapping-bank sorting still need a real VR headset/GPU check. Few triangles alone do not establish the final frame time. Narrow geographic batches and a small billow clusters rather than full-bank stacked shells reduce avoidable overdraw; extremely low viewpoints directly through multiple banks are less favorable than the intended above-cloud decks.

Implementation references checked against Unity 2022.3:

- [Unity single-pass instanced custom shaders](https://docs.unity3d.com/2022.3/Documentation/Manual/SinglePassInstancing.html)
- [Unity ShaderLab Blend](https://docs.unity3d.com/2022.3/Documentation/Manual/SL-Blend.html)
- [VRChat world project setup](https://creators.vrchat.com/worlds/creating-your-first-world/)

These references support the shader conventions, not a claim that this project has been compiled or profiled in Unity/VRChat.

## glTF / Blender preview integration

The existing `world_geometry.py` exporter originally forced `alphaMode='OPAQUE'` except for cutouts and recognized double-sidedness only for foliage/roof tiles. For these clouds, the integration owner should honor material metadata:

```python
alphaMode=m.get('alphaMode', 'MASK' if m.get('alphaClip') else 'OPAQUE')
doubleSided=m.get('doubleSided', False) or m.get('shader') == 'Foliage' or name == 'Kawara'
```

A glTF file cannot contain the executable Unity procedural shader. `alphaMode='BLEND'` alone cannot reproduce its varying density, so the preview must call the provided helper after GLB import and manifest loading:

```python
from cloud_sea import configure_blender_clouds
cloud_preview_info = configure_blender_clouds(bpy, manifest)
```

When invoking a Blender script outside `Source`, add the source directory to `sys.path` first. The helper changes only imported cloud materials and their shadow/smooth-shading flags. It uses the **actual imported mesh**; it creates no replacement cloud geometry or volumetric boxes. The Blender shader is an explicit visual equivalent using a radial edge fade, world-space procedural noise and diffuse relief. Noise and lighting are not bit-for-bit identical to Unity's shader. The helper returns JSON-safe material/object counts for the preview report.

Any final image must remain labeled “Blender geometry/material preview, not Unity or VRChat runtime.” Elevation and scenery changes belong in the source geometry before export, not as undocumented preview-only transforms.

## Billow refinement checkpoint

The first integrated overview exposed a visual defect: very wide, shallow caps read as flat plates despite procedural shading. The revised geometry replaces each cap with nine unequal rounded volumes, gives each volume its own local radial fade, varies the peaks, and uses noise-disturbed edge density. The bank centers and eight geographic batches stay unchanged. North/south openings remain actual geometry gaps.

## Verified checks

Isolated deterministic build, seed 12040:

- Geometry: 28 banks / eight batches / 36,288 triangles / 20,412 vertices
- All vertex/UV values finite; indices valid; no degenerate faces; every projected triangle faces source +Z
- Fixed-seed static altitude: 110.280–123.820 m; all generated configurations clamped inside the documented altitude envelope
- No collision geometry, file uploads or external publication performed
- JSON metadata round-trips successfully
- Twelve independent RNG seeds passed the geometry, altitude, budget, untouched-existing-data and two viewing-segment checks
- Clear north view segment: source `[-24,30,153.7] → [0,740,28]`, zero intersections with actual generated cloud triangles
- Clear south view segment: source `[-24,-40,153.7] → [0,-1400,0]`, zero intersections with actual generated cloud triangles
- Material hook executed successfully in Blender 4.3.2 / Cycles on the exported cloud GLB
- The first isolated 1000×625, 24-sample Blender render showed the road, city, forest and mountains through the northern opening. The billow refinement was then inspected against the actual integrated v2.6 world, replacing only the cloud mesh/material in a temporary preview scene at the same overview camera

The isolated render intentionally does not claim to show the integration owner's final raised-alley/peer-tree build. Final integrated renders should be regenerated after the complete world build.

Still unverified: Unity shader compilation, stereo headset appearance, VRChat Build & Test, GPU overdraw cost, transparent ordering from all walkable viewpoints, and final Windows world download size.

## v2.13 depth revision

See [CloudDepth.md](CloudDepth.md) for the literal opt-in Z-only source pass, exact eight-payload protection, current bounds and unchanged horizontal openings. Original cloud generation and shader code remain unchanged.
