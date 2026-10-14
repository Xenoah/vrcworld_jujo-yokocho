# Eight distinct venues, v2.16 authoring revision

Current v2.17 branding uses the eight RPG names listed in RELEASE_NOTES_2.17.0.md. The original design names below identify the v2.16 architectural design history, not the current visible sign text. Furniture, seats and physical layouts remain unchanged in v2.17.

The eight locations, deck footprints, outer circulation, and fall barriers remain fixed. The previous repeated shop shell, counter, furniture, and signage are replaced rather than covered with additional props.

| ID | Venue | Architectural and interior identity | Seat IDs retained |
|---|---|---|---:|
| S01 | 炭火 梢 | Pitched timber roof, charcoal hood and grill, heavy square stools | 6 |
| S02 | 麺処 風待 | Tiled noodle counter, enamel signage, tubular diner seating and preparation return | 6 |
| S03 | おでん 灯 | Curved awning, split benches, central serving-pot island | 5 |
| S04 | スナック 根っこ | Upholstered banquette, rounded backed stools, bottle-keep wall and chandelier | 6 |
| S05 | 枝先茶屋 | Open lattice salon, two four-place tea tables, broad central entrance | 8 |
| S06 | 宵葉 | Stepped walnut cocktail bar, backed stools and club chairs, geometric backbar | 6 |
| S07 | 山椒 | Listening chairs, perpendicular bar, record library and speaker cabinets | 6 |
| S08 | 木の実 | Arched confectionery display, gift boxes and wagashi, round pedestal seats | 6 |

Three of eight venues are nightlife venues (37.5%), interpreting the request for roughly thirty percent. The total remains 49 named stations; retaining a station count is not evidence that seating works in VRChat.

## Safety and preservation scope

The replacement owns only explicitly enumerated shop visual batches, station records, shop BoxCollider proposals, shop light records, and cooking steam records. Original external herb planters and underside structural braces remain byte-exact. Distant scenery, mountain revisions, stage, stairways, outer floors, safety walls, other lights, and unrelated colliders are protected separately.

Offline checks use actual final visual and collision triangles and complete oriented collider volumes. Entrance and staff/service paths must support a radius 0.325 m, height 2.2 m envelope. Seated torsos use a separate radius 0.28 m envelope above the authored station datum near the cushion top. A radius 0.25 m continuous seat-to-exit sweep is an additional conservative layout rule, not a simulation of VRChat: [VRCStation](https://creators.vrchat.com/worlds/components/vrc_station/) transports the user to its supplied exit transform when unseated. Avatar dimensions, IK, room-scale movement and Unity collision execution remain untested.

## Rebuild requirement

Use the complete matching v2.16 source and rebuild the scene. Do not swap only the visible GLB/native mesh into an older generated scene: old counter colliders and station positions would then be inconsistent with the new interiors. Rebuild lighting and reflection probes after generating the matching scene. The GLB/Blender images are editable-source previews, not the Unity scene or evidence of runtime performance.

## Review status

The accepted final source has native SHA256 `f52f44353420638bb500afd37f04b9c55d7f30ab4da4c369ad4b4c98080e3c46` and editable GLB SHA256 `65fdc1ce1da77db04ceae244ae2089852756705dd89f60e735b177336b6a0b15`. The literal v2.16 contract pins 291 shop batches, 815 unchanged nonshop batches, ordered keys, all manifest fields and eight source/profile/texture dependencies. The 40 retained herb/structural components are independently checked.

Independent final-model preservation, GLB and access audits pass. All 208 required probes pass and all 49 exit positions connect to their shop entrance component. Thirteen optional larger-radius guest diagnostics intersect furniture; this does not pass every path for arbitrary body sizes. Required entrance/staff/service paths use 0.325 m radius and 2.2 m height; customer paths and continuous transfers use 0.25 m radius. The separate torso envelope is 0.28 m. These are authored design envelopes, not avatar IK or runtime certification.

The initial integrated trials exposed actual backrest, staff-turn and retained-planter conflicts. Those were corrected in source, without excluding chair backs or dropping geometry from the tests. The final near-degenerate projected-triangle union failure was resolved by buffering every polygon, line and point before union, with an exact failure-replay test; no obstacle is silently skipped.

The original 107 noren component slices describe the historical v2.15 shop design, not the replacement. Historical inverse tests reconstruct that exact prior world before running its original invariants; current shops must independently match the complete v2.16 oracle. Unity compilation, lighting/probe baking, VRChat Build & Test and headset testing remain pending.

## Station datum details

Stations use deliberately rounded authored datums near, not exactly on, visible seat surfaces. Approximate offsets are 10 mm for ramen, 31 mm for oden, 31.5 mm for tea and 7.5 mm for sweets. These are explicit source values, not transform errors or completed VRChat seating/IK calibration. Confirm poses and egress using representative avatars during runtime testing.
