# Immutable shopfront print regression fixtures

- `shopfront_identity_before.py` is the exact generator before print-AA work.
- The original shipped 2048 × 2048 RGB atlas is represented by its immutable
  SHA-256 digest, not a redundant 4,177,023-byte packaged PNG.
- `world_geometry_before.py` is the exact pre-feature exporter regression fixture.
- `fixture_manifest.json` documents checksums and the validated toolchain.

The test pins the old Python source hashes as literals and checks them BEFORE
loading them. The old atlas is regenerated in a temporary directory with the
required fonts and must match the literal shipped digest
`8afee5ad6ca5368d89499af353b0829a15f54a56131aa79cde298a5fc572ac85`
BEFORE any candidate pixel comparisons run. Those exact regenerated original
pixels feed every A/B invariant. Do not replace this reference with candidate
output or update expected hashes merely to make a regression pass.
This retains the full byte/pixel proof without shipping a redundant atlas.

## Required authoring fonts

The original generator's fallback order and paths are part of this proof. Both
of these exact OpenType Collections must be installed on the test machine:

- `/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc`
- `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`

Their required SHA-256 values are pinned in the test and this manifest. These
are normal Noto CJK system fonts (commonly packaged as `fonts-noto-cjk` on Debian
and Ubuntu), not files to put in the Unity asset or source package. A different
font revision may rasterize differently, so matching names alone are not enough.
No font is downloaded by the test. Missing or mismatched fonts fail with an
explicit error rather than silently skipping any pixel proof.

The validated environment was Python 3.12.14, Pillow 12.3.0, NumPy 2.5.4.
The literal historical shipped-atlas hash remains the authority. Library/font upgrades that
change it require a separately reviewed fixture change, not an automatic update.

## Run from the project root

    python Source/test_shopfront_print.py --report Docs/shopfront_print_validation.json

`--project` defaults to the directory above `Source`; use it explicitly only
when testing a staged candidate against another project's geometry/layout.
`--report` is required so the result is written only to an explicit destination.
Temporary generated atlases use the system temporary directory and are removed.
The test does not regenerate the project or change production textures/meshes.
