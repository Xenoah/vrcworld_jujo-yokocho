# v2.19 independent source and art review

The accepted after-oracle is `c6f9ba4cacfd706382376ec7d6084187eca5933b331621db3d0afa159f259366`. Independent review confirmed the exact candidate native `5c747087ae2327374123be906bdcc5139909c9a30ad89487ade275fb4839674a` and GLB `32ec5b383c6586fa3568a4427d1d45dd82d77a24aa9f41e36a56dd647aaea0f1`.

- All 1,107 previous native batches remain byte-exact. Materials, lights, seats, collision and safety metadata are unchanged.
- All 4,576 old GLB accessors and 4,609 old buffer views are preserved, with only explicitly enumerated existing material/image activations.
- All 103 approved dependency hashes match. The new contract authenticates current data before projecting to immutable prior contracts.
- The exact final candidate passes all 208 required source-geometry access probes. These use specified design envelopes, not arbitrary-avatar or VRChat runtime simulation.
- All eight actual-model sign views were inspected. S05 has a disclosed limitation: its cup/moon relief is identifiable close up but hard to identify from shaded street approaches. The main fascia remains readable; no lighting or image brightening conceals this limitation.
- The six reporting mutation tests pass and bind counts to current authenticated native/GLB bytes.

The complete source and clean-extraction regression results are recorded separately. Unity compilation, baked illumination, stereo/headset performance and VRChat runtime remain unverified.
