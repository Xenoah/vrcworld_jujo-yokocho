# Entrance plaza addon, local review candidate

This is a separate, source-authored addon for the immutable TreeTopYokocho v2.19.0 checkpoint. Nothing has been published and Unity/VRChat execution is not claimed.

## Integration contract

Copy Assets/TreeTopYokochoEntrySystems/EntryPlaza and Editor/EntryPlazaBuilder.cs (including their supplied metadata) to the owner's addon tree. Do not place them under Assets/TreeTopYokocho, regenerate the core, or parent the addon under TreeTopYokocho_v2.

The owner calls TreeTopYokocho.EntrySystems.Editor.EntryPlazaBuilder.Preflight() before scene writes, then Build(root, generatedAssetDirectory). The root must be the identity scene-sibling EntrySystems_v1. The owning installer must create a fresh Assets/TreeTopYokochoEntrySystems/Generated/EntrySystems_N directory and own rollback. The builder creates only EntryPlaza beneath that root and a fresh EntryPlaza asset subdirectory. It refuses in-place overwrite, does not create the root, does not save or replace scenes, and never uploads.

Preflight authenticates the exact reviewed declarative JSON, native mesh bytes and eight authored PNGs against literal SHA-256 values in the builder. Source generation intentionally does not update these pins. Any geometry, destination, config or atlas change requires a new explicit review and pin amendment. Preflight also pins the immutable core manifest, checks exact G0/L2/L3 arrival heights, finite vectors/axes/ranges and native geometry counts.

The source-authoring Python reuses the baseline Geometry and chamfered timber primitives read-only; all new shapes, timber/endgrain textures, pictogram and Japanese print are authored here. Fonts are the baseline's full OFL KleeOne fonts, with verified glyph coverage. No assets were downloaded for the addon.

## Physical layout (source X east, Y north, Z up)

- All additions use the existing L1 floor at Z=134 m. No floating/new deck slab is added.
- Guideboard: center X=-5.1, Y=-32.3, width 3.0 m; main board Z=135.12 to136.72. It faces +Y. Three hanging wooden warp labels are at X=-6.05/-5.1/-4.15, Y=-32.18, Z=134.90.
- Warp destinations reuse the verified original landing X=-16,Y=-18.55 with Z=0.08/140.08/146.08. They are click/interact only, never automatic trigger teleports. The original YokochoTeleport behavior and core YokochoSafety are reused. The existing core lift roster is not copied or modified.
- Control frame: anchor (-8,-31.8,134), width1.65m; body Z=134.80 to136.05. Actual printed panel is Y=-31.714; the front frame reaches approximately Y=-31.645. The reserved mounting/front plane is Y=-31.62. Runtime button face is Y=-31.571, clear in front of the frame. The decorative title sits above the interactive panel at Z=136.15.
- Control standing point: (-8,-30.5,134). Owner controls use source X=-7.64 for visual-left column and X=-8.36 for visual-right column when viewed from +Y. Row heights are135.50/135.26/135.02, each trigger size (.60,.035,.19). The viewer-left/right index order and final .24m row spacing were coordinated with the owner. Lowest label edge134.925 clears the panel lower bound134.90.
- Log benches: centers(-6.15,-27.95) and(-8.65,-29.75), seat height134.56. Stump table center(-7.65,-28.90). They are static furniture, not extra VRCStation seats.
- Guide and controls approach routes, warp standing locations, button reservation and all collider boxes are explicit in EntryPlaza.json.

Unity conversion is (sourceX,sourceZ,sourceY), with native triangle winding reversed. Front-facing (+sourceY) printed planes place U=0 on +sourceX, because that is the viewer's left. The owner corrected its runtime control UVs to match this and reversed button pair X ordering for intuitive visual-left labels.

## Verification and evidence

The offline native-mesh audit passes:

- 33 furnishing collider envelopes have no core visual/collision triangle intersection above intended floor contact; all footprint samples have actual native collision-floor support.
- Four added swept paths and12 standing/arrival/spawn capsules have .325m radius and2.2m headroom, against original native visual meshes, original native collision meshes, explicit oriented solid boxes, actual added visual triangles and new solid boxes.
- All7 original declared navigation paths retain their full original width against the additions, including W01's2.4m width. All49 original seat exit capsules remain clear of additions.
- Zero overlap between independent furniture assemblies. Joinery contacts within a single board/bench/table assembly are intentional.
- All four spawn coordinates,49 stations and original lift declarations remain exactly preserved. No new lights, probes, VRCStation seats or core materials are introduced.

The final native addon contains2664 triangles in43 authored batches, merged by the Unity builder into12 material renderers. It adds33 solid boxes and3 small interaction triggers. Geometry and all baked texture bytes reproduce from source. Source tests additionally verify literal pins, exact warp targets, ownership, finite values, recovery reuse, Japanese glyph coverage and C# syntax.

Reports are entry-plaza-geometry-audit.json, entry-plaza-contract-tests.json and entry-source-reproduction.json. These are static/offline checks, not a Unity or Udon compiler, CharacterController simulation, room-scale avatar test, performance measurement, multiplayer test or VRChat Build&Test. A .06m foot-contact tolerance excludes native floor thickness; routes and furniture are still supported by actual collision triangles.

## Native previews

The PNGs are rendered from the exact native v2.19 local entrance triangle excerpt plus EntryPlazaMeshes.bytes. They are not concept images. The excerpt omits distant scenery and uses review-only soft lights; no preview lights are installed into Unity. Runtime dynamic status is not simulated.

- entry-plaza-native-oblique.png: clear scale/readability view of the native boards, log furniture and retained deck/railings.
- entry-plaza-native-eye.png:1.70m eye height from audited SpawnToGuide vertex(-3.7,-28.6).
- entry-guideboard-interaction-distance.png: guideboard at the audited1.50m approach distance,1.65m eye height, to inspect dark-ink text and primary warp labels.
- entry-controls-static-layout.png: optional exact owner's six static button planes/atlas, including corrected U and column order. It verifies static layout, not Udon runtime. The provenance report pins owner atlas/installer bytes used.

The blank control panel in earlier images was intentional; controls are owned by the systems installer, not duplicated in the plaza native mesh. Obsolete pre-fix images are not deliverables.

## Reproduction

From a checkout with the approved baseline and Python dependencies installed:

    python Source/build_entry_plaza.py /path/to/immutable/TreeTopYokocho /path/to/output
    python Source/audit_entry_plaza.py /path/to/immutable/TreeTopYokocho /path/to/output
    python Source/test_entry_plaza_contract.py /path/to/immutable/TreeTopYokocho

Source generation never updates the reviewed builder hashes. Run the contract check against the final reviewed staging root. Blender proof:

    blender -b -t4 -P Source/render_entry_preview.py -- BASELINE_ROOT OUTPUT_ROOT OWNER_SYSTEMS_STAGE

The optional final argument enables the static owner-label preview and asserts its reviewed UV/column convention.

## Remaining owner acceptance

Import the combined addon into the built v2.19 scene, compile C#/Udon, run the owner's installed-scene audit and verify click targeting from each approach. Check destination arrival and recovery updates, staying seated behavior, six controls and status readability, current Unity lighting, headset scales/room-scale movement and final performance. Retain the original49 stations and existing lift audit results. No publication is requested or performed by this worker.
