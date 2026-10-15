# Entry systems integration plan (unpublished)

Published v2.19 remains the immutable rollback. Install the separate `Assets/TreeTopYokochoEntrySystems` folder only after generating the core scene. The addon is not covered by the old 61-stage core test result.

- Scene root: `EntrySystems_v1`, sibling of `TreeTopYokocho_v2`.
- Children: `EntryPlaza`, `SystemsControls`, `GlobalClock`, `LocalBGM`.
- Menu: `Tools/TreeTop Yokocho/8 - Install Entry Systems (Add-on)`.
- Installer must preflight the current supported core source manifest, one identity-transform core root, active scene, imported scripts and supported sky properties before asset/scene changes.
- A matching complete install is a no-op. An ambiguous/partial/foreign root fails closed; no automatic destructive replacement.
- Generated assets use a unique addon-owned directory. Installation failure rolls back only objects/assets created by that invocation and restores the prior scene sky reference.
- The sky is cloned. Core material assets, geometry, collision, stations, light settings and existing interaction objects are not edited by installation.
- The runtime clock may change scene sky, ambient, fog and the existing directional key. Static baked lightmaps/probes remain at their baked state; no dynamic rebake claim.
- Clock state is global. Music is local per user, starts OFF, and consumes only imported `.mp3` clips in the designated addon Music folder. Empty playlists are valid and silent with explicit status.
- Controls use Japanese baked labels and ASCII dynamic clock/music status. No runtime Japanese system-font dependency.
- Core rebuild generates a new scene/root; reapply this installer. Do not copy addon scene objects between unrelated scenes.
- Offline geometry checks and source/API checks cannot establish Udon compilation, network synchronization or in-headset usability. Those remain explicit Unity/VRChat acceptance steps.
