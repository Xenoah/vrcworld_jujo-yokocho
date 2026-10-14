# Atlas-specific procedural cloth frequency correction

Owner selected this narrow correction after the source audit measured broad9–11cm procedural periods on actual ShopfrontTextile. This is not a change to albedo sampling, lettering, atlas coordinates, geometry, normals from imported textures, roughness, sheen, strength or animation.

Changes:
- ShopfrontTextile only: `_WeaveScale96→4096`.
- Unused Noren0–7 and CityWovenBanner keep96, with existing separate culling semantics.
- Cloth inspector range becomes8..4096 (only as wide as needed); default remains96. Label says procedural cycles per UV repeat, not a guarantee of physical thread density.
- The shader implementation, derivative filter, strength.045, sheen.055 and meta guard remain byte-identical outside that property line.
- DarkTimber routing is exactly unchanged. Whole-profile hash changes and therefore any external full-profile dependency must be explicitly repinned after review.

Actual source measurement used8,636 triangles in current ShopfrontTextile with area≥.0008m², excluding tiny hems/tabs and degenerate UVs. Principal UV-frequency percentile10/50/90 becomes395/463/515 cycles per metre in one principal direction,315/390/395 in the other. Median periods are2.16mm/2.57mm. The diagnostic does not claim all hems or folded regions have uniform thread dimensions.

Existing fade is `1-smoothstep(.20,.50, max(fwidth(thread.x), fwidth(thread.y)))`. Representative median principal-frequency footprints:
- .10mm or.25mm per pixel: full amplitude in the assumed principal/diagonal cases.
- .50mm:96.9% in the principal case,61.2% at the diagonal upper-footprint estimate.
-1mm:4.19% principal,zero diagonal estimate.
-2mm and5mm:zero.

These are specified world-pixel-footprint diagnostics, not measured headset pixels or actual eye-space rendering. They deliberately show that micro-weave may disappear at ordinary viewing distances. No visible micro-weave, alias-free VR rendering or comfort claim is made. Geometric drape and broad light-driven cloth response remain when procedural detail fades.

Three staged tests pass: routing-only scope including exact DarkTimber preservation, only the inspector property line changes in shader, and monotonic attenuation/period metrics. Runtime shader import/compile/stereo still needs Unity.

Independent full-cloth check (preferred physical U/V evidence): all27,534 faces, with27,246 valid in both UV gradient rows. Using area-weighted actual row norms of `J = Duv @ pinv(Eworld)` gives U period P10/median/P90=2.530/2.533/3.127mm and V=2.057/2.157/2.400mm. Degenerate UV faces account for.13383m² of36.60672m² and are explicitly excluded from period quantiles. At96, weighted median U/V periods were108.069/92.014mm. See `cloth_weave_independent.json`.

Those U/V values are not the same statistic as the earlier area-filtered principal/singular-value diagnostic. Both are labelled separately rather than conflated. Neither proves runtime visibility or VR alias behaviour.
