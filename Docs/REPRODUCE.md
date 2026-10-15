# Reproduce the original PBR source and comparisons

## Start from the integrated package root

Run the commands below from the directory containing `Source`, `Assets`, `Docs`
and `Preview`. Use a working copy if the reviewed outputs must remain untouched.
The active proof scripts use the immutable core already in this same package:
`Source/TreeTopYokocho.glb` and
`Assets/TreeTopYokocho/Data/WorldManifest.json`. They never rewrite those inputs.

Use the Python, NumPy, SciPy and Pillow versions recorded in
`Docs/authored_pbr_origin.json`. Map synthesis uses no network, source photograph,
scan or model-generated bitmap. Blender is needed only for proof rendering.
The supplied evidence was rendered with Blender 4.3.2 and Cycles CPU.

## Generate and validate maps

    python -B Source/author_seamless_pbr.py
    python -B Source/validate_authored_pbr.py
    python -B Source/validate_multiscale_seams.py

The generator writes 16 PNGs, four contact previews, four family reports and one
origin manifest. The 92-check validator independently decodes the PNG contracts.
The 80-check validator evaluates all 16 maps at five area reductions. Both reports
record the exact origin SHA-256. Neither grants artistic or Unity runtime approval.

For a byte-exact independent rerun, create a new empty directory with `Source`,
`Docs` and `Preview`, copy only `Source/author_seamless_pbr.py` into it, and run
that copy with the recorded dependency versions. Its root is the parent of
`Source`. All 16 PNG hashes, source/origin hashes and four contact hashes must
match: 22 checks. No absolute workspace path enters the generated origin.

## Rebuild the full paired comparison set

Set `PYTHONDONTWRITEBYTECODE=1` in the shell used to launch Blender so imports do
not create bytecode files in the immutable core. For a POSIX shell use
`export PYTHONDONTWRITEBYTECODE=1`; for PowerShell use
`$env:PYTHONDONTWRITEBYTECODE="1"`.

    blender -b -t 4 -P Source/render_material_proofs.py -- baseline studio
    blender -b -t 4 -P Source/render_material_proofs.py -- authored studio
    blender -b -t 4 -P Source/render_material_proofs.py -- baseline tile
    blender -b -t 4 -P Source/render_material_proofs.py -- authored tile
    blender -b -t 4 -P Source/render_actual_trunk.py -- baseline
    blender -b -t 4 -P Source/render_actual_trunk.py -- authored
    blender -b -t 4 -P Source/render_trunk_light_sweep.py -- baseline
    blender -b -t 4 -P Source/render_trunk_light_sweep.py -- authored
    blender -b -t 4 -P Source/render_actual_rock.py
    blender -b -t 4 -P Source/render_world_texture_study.py -- baseline --views deck_walk yakitori_service alpine_city --width 1200 --samples 24
    blender -b -t 4 -P Source/render_world_texture_study.py -- authored --views deck_walk yakitori_service alpine_city --width 1200 --samples 24

These commands write fresh comparisons under `Preview`: 2 studio, 10 trunk,
8 physical-scale 2 by 2 tiling, 2 actual-rock and 6 full-world images. Authored
metadata records the active script and current origin hashes. Geometry, UVs,
material tints and world lighting remain the original inputs. Rendering is not
promised byte-identical across Blender, CPU and platform versions.

The optional world-only denoiser is the unchanged core `denoise_preview.py`.
Pass explicit PNG filenames, not directories, and use the same operation on
both sides of the comparison:

    python -B Source/denoise_preview.py Preview/world_baseline/Blender_deck_walk.png Preview/world_baseline/Blender_yakitori_service.png Preview/world_baseline/Blender_alpine_city.png
    python -B Source/denoise_preview.py Preview/world_authored/Blender_deck_walk.png Preview/world_authored/Blender_yakitori_service.png Preview/world_authored/Blender_alpine_city.png

It retains the raw PNGs under `Raw` and records raw/output/denoiser hashes in each
JSON. Neutral studio, tile, trunk and rock proofs remain undenoised. Install the
denoiser's dependencies from the core's dependency instructions if this optional
step is required.

## Evidence roster and acceptance

`Source/freeze_pbr_evidence.py` packages exact source, map, document and preview
hashes. To rerun it, name the independent generation directory `ReproductionFinal`
and provide the complete paired proof set above. It verifies 22 reproduced files
and current-map bindings before writing `Docs/texture_candidate_manifest.json`
and `Docs/proof_integrity.json`. The independent generation directory is working
material and is not part of the public package.

`Docs/RenderSourceHistory` preserves exact earlier proof-source bytes and their
hashes. Historical images remain evidence from those recorded versions, not a
claim that a later script rerendered them. Final adoption is recorded separately
in `Docs/ORIGINAL_PBR_REVIEW.json`; these Blender comparisons do not establish
Unity/VRChat importer, compression, shader, parallax, mipmap or runtime results.

## Optional standalone-material fallback

If a standalone material directory lacks either of the two core files above,
the proof scripts fall back to a sibling `tree-baseline-v219/TreeTopYokocho`
directory containing the complete immutable v2.19 core, its renderer and local
dependencies. Map synthesis itself needs no baseline. The integrated package
uses its own core first and does not need this sibling layout.
