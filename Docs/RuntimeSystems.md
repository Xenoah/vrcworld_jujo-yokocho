# Entry Systems runtime contract 0.1.0

## Scope and honest validation status

This is an optional source add-on for the released TreeTopYokocho v2.19 baseline. It does not replace or modify the core builder, runtime scripts, shaders, audio, lightmaps, probes, or manifest. The only runtime classes are in `Assets/TreeTopYokochoEntrySystems/Runtime/`.

The baseline declares Unity **2022.3.22f1** and Worlds SDK **3.10.5**. Explicit `NetworkCallable` handlers need SDK 3.8.1 or newer. Use the project's supported VCC/SDK setup; do not import old SDK unitypackages alongside it.

C# grammar parsing, source contracts and executable reference-model tests pass. These are **not** Unity import, C# assembly compilation, UdonSharp compilation, ClientSim, VRChat multiplayer, audio, or headset validation. The reference models are separate Python specifications, not a Unity emulator. Those execution gates remain mandatory before an upload is called ready.

## BGM: local, random, safely empty

- `YokochoBgmController` changes only the visitor who presses the entrance switch. It does not synchronize ON/OFF, song, position or volume with other visitors.
- Safe default: OFF. The existing archive contains `Assets/TreeTopYokocho/Audio/CanopyWind.wav` and **no MP3 tracks**. Wind ambience is not music and is not silently put in the playlist. No songs are supplied by this add-on.
- The installer must collect only `.mp3` assets that successfully import as `AudioClip`. Assign an empty array when none exist. Import metadata/decoding is handled by Unity, not a runtime file search.
- Empty/all-null/zero-length playlists are silent. The entrance status shows `BGM LOCAL OFF / NO MP3` or `BGM LOCAL ON / NO MP3`. A missing source shows `SOURCE NOT SET`.
- With valid tracks, random selection excludes the immediately previous track when another playable track exists. One track repeats. Music fades in and OFF fades out; selecting the next song stops the old source, so this is not a crossfade system.
- A source that fails to start has three seconds' grace, then five seconds' backoff. Retry expiry is evaluated before the stopped-song test, including for long clips. Failed clips are quarantined for that listening session; if all fail, automatic attempts stop. OFF then ON retries. A late decoder start during the backoff cancels that backoff.
- Use a dedicated AudioSource. Do not share it with wind ambience, effects, an Animator, another player, or a script that changes clip/pitch/pause state. The controller owns that source and fixes pitch at 1.
- The installer should configure `playOnAwake=false`, `loop=false`, modest volume, and the intended 2D/global-listening spatial setup. The controller also enforces the first two at Start. The visitor's VRChat world-volume settings still apply.

## Global clock modes

| Mode | Behavior |
| --- | --- |
| Initial/manual | Default 18:30, frozen. Previous/next move one hour and wrap modulo 24. Presets: 00:00, 06:00, 12:00, 18:30. |
| AUTO JST x1 | Uses SDK network UTC plus nine hours. It does not trust a visitor's PC timezone or independent device wall clock. |
| JST START xN | On entering acceleration, the owner captures current JST and server time. All clients derive `(anchorHour + serverElapsed * multiplier / 3600) mod 24`. |
| Speed sequence | 2, 5, 10, 30, 60, then real JST x1. Changing between accelerated rates retains the simulated instant. Selecting Auto or wrapping to x1 deliberately returns to actual JST. |

This is an artistic day/night cycle, not a latitude/date-dependent astronomical sun simulation. The status reports the authoritative target time; the visible atmosphere eases toward it locally to avoid sudden flashes. During that short transition, visitors may see slightly different intermediate blends due to frame/network timing. They converge on the same retained mode and timeline.

### Networking invariants and limits

1. Exactly one `YokochoGlobalClock` is installed. Its current object owner writes the six synchronized scalar fields: initialization, mode, manual hour, multiplier, simulated-hour anchor and server-time anchor.
2. Buttons invoke underscore-prefixed local APIs. Those send only allowlisted commands to the current owner. No button calls `SetOwner`; no logic depends on instance-master identity. Owner handlers have explicit `NetworkCallable` annotations, four events/second per handler, plus a combined 0.25-second acceptance guard. Local request cooldown is 0.4 seconds. Competing/very fast commands may be ignored, not queued indefinitely by this code.
3. Owner initialization waits for `IsNetworkSettled`. Late joiners receive retained synchronized values, not a replay of historical button events. Deserialization only updates display; it never sends a button command or takes ownership.
4. Manual serialization is dirty-state based. Multiple changes before the actual serialization snapshot coalesce. Changes after `OnPreSerialization` remain dirty for a later send. Failure schedules a two-second retry of the latest state. There is no per-frame state broadcast.
5. Accelerated time is re-anchored at most once per ten minutes while the owner is active. The SDK's `CalculateServerDeltaTime` handles the wrapping server-time representation. Re-anchoring preserves the simulated instant; it is not a reset to current JST.
6. Ownership transfer/master departure keeps the already synchronized mode, multiplier and anchor unchanged. The new owner re-advertises that state. Disable/re-enable clears stale local send-queue bookkeeping without resetting network state.
7. A button request still in flight, or a local owner change not yet serialized when the owner leaves, is **not guaranteed durable**. The successor retains the last successfully replicated snapshot. This is not a transactional acknowledgement protocol. Re-press a control if its result did not replicate. Owner suspension can delay new commands until VRChat recovers/transfers ownership.
8. No persistent per-user data or cross-instance state is stored. A fresh instance begins at its configured defaults.

## What the time changes, and what stays baked

The controller snapshots the scene baseline at Start and restores it on disable. At manual 18:30 it uses the authored dusk baseline. At other hours it blends:

- the existing directional key's transform, color and intensity;
- the custom sky's `_Zenith`, `_Horizon`, `_SunsetColor`, `_SunsetDirection`, `_HighCloudTint`, optional `_StarStrength` and `_AuroraStrength`;
- RenderSettings fog color and trilight ambient colors.

Fog density, ambient intensity and sky strength retain their authored values. The existing sky shader/keyword, cloud shape, aurora motion, post-processing and lanterns are not replaced. There are no added realtime point lights or strobe effects. Stars/aurora fade down in daylight without raising their authored maximum strengths.

The baseline key `BlueHour_Key` is Mixed with IndirectOnly lighting, so its realtime direct contribution can change. **Baked indirect lightmaps, baked lantern/fill contributions, baked probe lighting and baked reflection textures remain fixed.** Changing RenderSettings ambient values does not rebake static GI or light probes. The daytime/nighttime results may therefore contain deliberate dusk-lighting remnants. This add-on must not be described as full dynamically rebaked 24-hour lighting.

`fillLight` identifies the existing `Sunset_WarmFill`; the runtime never animates its baked contribution. No bake is invoked at runtime. Preserve the core lighting settings and validate the mixed-light visual result in the actual client.

The installer must create and own a dedicated sky material clone. Never assign the core generated `Sky.mat` as `skyMaterial`. No second atmosphere controller, Animator, timeline or script should write these same RenderSettings/key/material properties concurrently. The add-on assumes exclusive runtime control of those properties.

## Serialized installer API

### YokochoGlobalClock

- `sun: Light` → existing `BlueHour_Key` directional light.
- `fillLight: Light` → existing `Sunset_WarmFill`, optional identification only.
- `skyMaterial: Material` → dedicated clone of the current authored custom sky.
- `statusText: TextMesh` → entrance time status.
- `initialHour: float = 18.5`, `startInAuto: bool = false`.
- `installationVersion: string = "0.1.0"`, `installedCoreManifestSha256: string = ""` → passive installer-owned markers; not network state. Installer fills the actual core manifest SHA-256.
- Local events: `_PreviousHour`, `_NextHour`, `_SetDawn`, `_SetNoon`, `_SetDusk`, `_SetMidnight`, `_SetAuto`, `_CycleSpeed`, `_ResetDusk`.

Do not wire scene buttons to the `Owner...` methods. Those are network receiver endpoints, not the local UI contract.

### YokochoBgmController

- `musicSource: AudioSource` → dedicated, non-play-on-awake source.
- `playlist: AudioClip[]` → imported MP3 clips only, stable asset ordering; empty is valid.
- `statusText: TextMesh` → entrance local-music status.
- `defaultOn: bool = false`, `volume: float = 0.22`, `fadeSeconds: float = 0.8`.
- Local events: `_ToggleMusic`, `_EnableMusic`, `_DisableMusic`, `_NextTrack`.

### YokochoEntryControl

- `target: UdonSharpBehaviour` → one of the above controllers.
- `eventName: string` → exact underscore-prefixed local API name.
- `cooldownSeconds: float = 0.4`.
- Interact requires the usual enabled collider and Udon interaction configuration on the physical button. No Canvas/slider is needed.

All dynamic status characters are printable ASCII (32–126) plus newline. Static Japanese labels can be baked separately; dynamic status needs no OS CJK font fallback. Preserve the provided `.meta` files when copying these scripts, so their GUIDs remain stable.

## Unity/MCP acceptance checklist

Do not mark these steps done based on the portable tests.

1. Import via the compatible VCC project and confirm all three scripts compile in Unity and UdonSharp without warnings/errors that affect execution. Confirm the cloned material uses `TreeTopYokocho/BlueHourSky` and the existing fantasy keyword state.
2. Run the non-destructive add-on installer once, then again. Confirm one add-on root, unchanged core object/material/audio values, correct passive markers, no duplicate controllers, dedicated source and sky clone, and readable labels/status.
3. In Play Mode verify the initial 18:30 matches the pre-install dusk, BGM is OFF, no-MP3 mode is silent, and disabling the controller restores the original settings. Re-enable and test again.
4. Add two rights-cleared test MP3s in a test copy, import, refresh the playlist through the supported installer workflow and verify random playback, no immediate repeats, OFF fade, next-track, missing source and failed-clip status. Do not silently add test music to a distributable.
5. Build & Test with at least two clients. Compare manual/Auto/accelerated time, then join a third client after each mode change. Check midnight, 60x, repeated speed changes, return to real JST and competing button presses.
6. Compare Auto against trusted current JST, including clients with different OS timezones. Confirm runtime SDK network UTC behavior, rather than relying solely on the editor's time provider.
7. Have the owner leave while accelerated. Check that the successor keeps the timeline. Also leave immediately after a command, under poor network conditions and while serialization is queued; document the last-replicated-state limit. Disable/re-enable while a send is pending and check recovery.
8. Examine noon, dawn, midnight and dusk in a headset. Check fixed baked-light/probe remnants, comfort, legibility, performance and the absence of flashing. Verify intended platform builds independently.
9. Only after those gates can a live-world result be claimed. This source package itself is not proof of VRChat upload or deployment.

## Portable checks

From the add-on project root, install `Tests/requirements-runtime-tests.txt` into a Python virtual environment, then run:

```sh
python -m unittest discover -s Tests -p 'test_runtime_*.py' -v
```

`test_runtime_source.py` parses actual C# grammar and checks its API, ownership, snapshot, retry and baseline contracts. `test_runtime_models.py` tests independent design models for timing, rollover, ownership snapshots, serialization coalescing and audio failure progression. It deliberately labels the distinction from real runtime execution.

## Primary API references

- [VRChat Networking API](https://udonsharp.docs.vrchat.com/vrchat-api/#networking): network date, server timestamps and delta API signatures; synchronized numeric types.
- [VRChat network events](https://creators.vrchat.com/worlds/udon/networking/events/): owner targets, explicit network-callable endpoints, underscore local methods and rate limiting.
- [VRChat network components](https://creators.vrchat.com/worlds/udon/networking/network-components/): network-settled and serialization/deserialization callbacks.
- [VRChat late joiners](https://creators.vrchat.com/worlds/udon/networking/late-joiners/): retained variable state rather than event history.
- [VRChat ownership](https://creators.vrchat.com/worlds/udon/networking/ownership/): owner reassignment and avoiding master-based authority.
- [Unity AudioSource.isPlaying](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AudioSource-isPlaying.html) and [AudioClip.length](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AudioClip-length.html): playback/clip-duration behavior.
- [Unity Mixed lights](https://docs.unity3d.com/2022.3/Documentation/Manual/LightMode-Mixed.html): realtime changes do not update baked contributions.

References checked 2026-10-14. The official network-date API listing is terse; the UTC/time-provider behavior remains explicitly included in the live-client acceptance checks above.
