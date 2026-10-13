# Exact v2.8 revision contracts

`verified_layout_2.6.0.json` remains the original immutable regression baseline.
The v2.8 shop-detail validator does not refresh that baseline or skip changed
collections. `Source/revision_contracts.py` validates these exact exceptions:

- **77 solid boxes:** the 16 authored counter trims (two per shop) must pass
  `validate_staff_access.intended_counter_changes`. Every record retains its
  original fields; the other 61 records must match completely. The preserved
  v2.7 solid-box collection must still hash to
  `119008866d3725961468ac7740bbf8ea46362f20f75ffe7073518fda6823e79c`.
- **12 lift controls:** `verified_lift_controls_2.7.0.json` preserves the original
  controls, whose collection hash is
  `ba815a559872a8c06830de0e504da16c44406f15cd1e288bdc7a80414a08cec4`.
  Only `position` and `size` change. Each source level uses its current floor Z;
  each destination index `k` in `G0, L1, L2, L3` gives the position
  `[-17.20, -19.20 + k * 0.64, z + 1.25]` and size `[0.30, 0.58, 0.50]`.
  Position comparisons allow only `1e-9 m` arithmetic tolerance. Names, order,
  destinations, forward vectors, labels and field sets remain unchanged.
- **599 protected geometry batches:** 598 retain their original hashes.
  `Tree/SupportingBranches`, material `Bark`, must change specifically from
  `193ef190f01988b59cf0198c9c4f42d45fed6b1bba5678f248495aa0fb896a71` to
  `8f6573d1bb4f319d7998c5371aa0fb9b7c894b3e56982476ffdfceb87492c48d`.
  The reviewed branch-control edits are `(branch 1, point 1, z=34.0)`,
  `(branch 1, point 2, z=40.0)`, and `(branch 3, point 1, z=37.5)`, using
  zero-based indices. Hash input is little-endian float32 vertex bytes followed
  by little-endian uint32 face-index bytes. Missing and duplicate protected
  batches fail, as does retaining the old branch instead of the reviewed one.
- **Collision source:** remains SHA-256
  `51e395fbea8f6d29ffbebe76bb484f465c671508f93bf75afa9294ccff630ddb`.
- **All other protected metadata:** stations, spawns, floors, stairs and crown
  stairs retain their v2.6 hashes with no exceptions.

The shop/railing clearance sweep uses `mainRingNavigation.points` and `.z` when
provided. Only a manifest lacking `mainRingNavigation` falls back to the old
radius-18 m, Z=140 m circle. Malformed authored routes fail validation rather
than silently falling back. These are offline source-geometry checks, not a
Unity/VRChat runtime or physics certification.

## Verification

On 2026-10-13, 2,345 in-memory positive/negative assertions passed. They covered
all 77 solid records, all 12 controls, protected-batch mutation/missing/duplicate
cases for all 599 batches, baseline tampering, field/count/order/type changes,
authored-ring coordinates, legacy fallback and seven malformed route fixtures.
The generated v2.8 shop-detail validator also passed all 11 checks against
745,110 actual shop/railing triangles. That verification captured its report in
memory and did not overwrite generated assets or reports.

The preserved `verified_layout_2.6.0.json` file SHA-256 was checked unchanged:
`5d58e8c0c6cd6605e7ae54d2cffbd725214417d61166c13f6a4ce441cb7b8324`.
