# Mountain quality: selected geometry, snow and shared normals

The selected revision combines adaptive sampling of the original analytic terrain, soft connected snow variation, and shared normals at eligible cross-material seams. Stronger dark snow masks and an optional snow normal texture were rejected. No new material or texture was needed for the selected snow treatment.

## Exact scope

Only twelve named distant mountain batches change geometry: 11,500 → 15,256 triangles and 7,461 → 9,690 vertices. The same horizontal domain, boundary sample locations and height function are retained. This is not an identical silhouette or identical Z envelope: maximum Z increases from 913.663757 to 924.522705 metres, and the largest measured summit-neighborhood gain is 13.990112 metres. Against a dense sample of the same analytic function, the specified 1280-pixel view's skyline RMS error improves from 2.637154 to 0.766987 pixels. This measures that diagnostic view, not every possible camera.

Eight exact snow-material records receive only RGB changes over the selected adaptive geometry. Soft connected smoothing breaks up broad blank snow while preserving white crests. Positions, UVs and indices do not change in this color pass.

Of 1,801 cross-batch shared positions, 1,765 are eligible for shared normals. A total of 3,637 normal slots changes. Thirty-six crease positions are excluded, preserving 89 edges sharper than 55 degrees. There is no global smoothing or modification of unrelated objects.

## Import precision and runtime limits

The GLB exporter validates the exact twelve source identities and appends only the admitted normal accessor data after ordinary serialization. The independent selective-PNG shop atlas option is preserved.

The Unity editor helper validates geometry before changing those normals, then recalculates tangents. Those twelve meshes are serialized only after the helper runs and use MeshCompression.Off. The separate exact city-roof exception also remains Off; other visual batches retain their existing Low setting. This avoids an unproved assumption that lossy compression preserves cross-batch seam coordinates and normals. Its Unity serialized/download-size cost is unmeasured.

Python and a scalar transcription of the C# formulas agree on the tested Float32 output, including reflected coordinates/winding. C# parsing and source guards are not execution of the Unity editor helper. Unity compilation, import, lighting bake, stereo appearance and runtime performance remain unverified.

## Reproduction and protection

Run `python Source/build_world.py .`, `python Source/pack_geometry.py`, then `python Source/run_checks.py` using the dependencies in Source/requirements.txt. The focused entry point is `python Source/validate_mountain_quality.py`.

The literal flags mountain_detail, mountain_snow_craft and mountain_seam_normals have explicit dependencies. Immutable v1/v2 test oracles admit only the twelve geometry and eight snow-color records. There is no mountain-prefix exemption. The actual native buffer is admitted independently of summaries. A test-only inverse composes with the city-cap and unused/sea inverses to reconstruct the exact original v2.14 native SHA; production admission never uses the inverse.

- [Current focused regression](mountain_quality_validation.json)
- [Bounds and summit measurements](mountain_bounds_and_summits.json)

Actual-model Blender comparisons informed selection. Blender's material response, atmosphere and antialiasing are approximations, not Unity runtime evidence.
