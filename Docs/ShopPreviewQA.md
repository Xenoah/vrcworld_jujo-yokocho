# Shop preview viewpoints and limits

Eight shop survey cameras now have explicit source-floor heights and individual body/support diagnostics. Four historical survey poses touched a lantern support or a railing/safety surface; only those cameras moved by 0.125 m. No world geometry, collider, navigation path or shop placement moved. Previous art-study images retain their original camera provenance and are not retroactively recertified.

- `preview_camera_validation.json`: all17 marked flat standing viewpoints, including8 shop surveys, pass9 support-ray samples and actual triangle/box surface checks for radius0.25 m, body height2.2 m, lower offset0.06 m.
- `shop_preview_route_validation.json`: every shop survey has a clear straight source connector from an authored route centerline. The full buffered connector footprint is tested against actual visual/collision triangles and77 explicit boxes. Floor support is sampled at no more than0.1 m intervals,9 rays per sample.
- `shop_preview_camera_adjustments.json`: exact old/new coordinates for the four corrected poses.

These are finite source diagnostics, not Unity avatar simulation, inside-only solid containment, arbitrary roomscale accessibility, eye comfort, or certification of every possible route. The sloped nearest-sea camera has a separate support/contact report rather than a fabricated flat-floor height.

Future gallery images must hash their actual GLB, camera definition, material/atmosphere profile and preview scripts. Blender images approximate the Unity shaders and do not establish runtime parity.
