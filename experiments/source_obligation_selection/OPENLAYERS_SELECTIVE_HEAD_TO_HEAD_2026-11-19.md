# OpenLayers cache-reuse comparison — 2026-11-19 (PRIVATE EXPERIMENT)

**Objective.** Compare two independently developed selective repairs under the same full-observation adversary, without altering upstream OpenLayers or MathGraph `main`. This is a repair-method comparison on an already known finding, **not** a new blind discovery by the MathGraph scanner.

## Exact source and lineage

- Upstream pin: `openlayers/openlayers@e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2`.
- URL-revalidation candidate: exact copied blob `be2b260ba153581fee76432c03d89d5e543e0a88` from `experiment/openlayers-pixelratio-selective-20261119`; no edit to its patch.
- Source-owned provenance v2: `experiment/openlayers-selective-ratio-v2-20261119` at `6a31c0445c811e2760ac37b9e7fdee9647bf4754`, patch script blob `4a825b12fd2c8d7474268e6f31f6579ae735e7bc`; originally proposed on earlier v1 branch, refined after detecting missing custom-loader qualification and base-method JSDoc/type issues.
- Both changed only temporary pinned checkouts in GitHub Actions. No upstream PR, no MathGraph main change.

## Bounded head-to-head

[GitHub Actions #44446054950](https://github.com/metalogiclabs/mathgraph/actions/runs/44446054950), exact browser job, [artifact #14493078087](https://github.com/metalogiclabs/mathgraph/actions/runs/44446054950/artifacts/14493078087) (SHA256 `f7b659e398b51c74ef9fe1dc74ed3a136267a8bb5b1c11cc2184203c11addac8`).

The unchanged 3-test Chromium adversary creates a source-owned generated **constant** tile URL but a custom loader that paints a color channel according to public `Map.getPixelRatio()`. A completed ratio-1 frame loads channel 50. A fresh ratio-2 map independently loads channel 200. Same-ratio repeated frames should reuse tile objects. Transition `Map.setPixelRatio(1→2)` must not silently retain channel 50 when the loader is ratio-sensitive.

| Tested implementation | Controls | 1→2 full loaded-image check |
| --- | --- | --- |
| Exact original | 2/2 pass | RED: old channel 50 retained, four loader calls |
| URL revalidation unchanged | 2/2 pass | RED: old channel 50 retained, four loader calls |
| Source-provenance v2 | 2/2 pass | GREEN: changed loaded image channel 200, 3/3 tests pass |

This **REJECTS the proposition that per-tile URL equality suffices for full loaded-image behavioral equivalence** under an admissible custom-loader configuration. It does not establish that the competing patch has no useful or correct applications.

## Other comparative controls — neither candidate dominates generally

- URL-revalidation patch: prior pinned mixed-URL control replaced 2/2 ratio-dependent entries and retained 2/2 independent entries within one source, [Actions #44444697115](https://github.com/metalogiclabs/mathgraph/actions/runs/44444697115), full browser **3,127/3,127**. This requires additional user URL callback evaluations and may perturb stateful callbacks; custom-loader behavior was not protected in the new test.
- Source-provenance v2: unknown/custom loader and URL functions conservatively invalidate, but factory-generated template + default loader + original tile-class/method guards preserve four tile objects with no URL re-evaluation, while correcting the ratio-dependent custom-URL test. Exact native Chromium **3,133/3,133**, all original-source upstream pretest lint/type/libtype checks green, [Actions #44444701473](https://github.com/metalogiclabs/mathgraph/actions/runs/44444701473), [artifact #14493181497](https://github.com/metalogiclabs/mathgraph/actions/runs/44444701473/artifacts/14493181497) SHA256 `497169d8ebb30c83903b918fe494c87fba5a0371c9f8142cba83de8abe85de10`. A custom ratio-independent URL callback still triggers four unnecessary recomputations under v2's conservative fallback.

**Epistemic boundaries.** WARRANTED_BOUNDED for these exact source-pinned browser tests and original source controls. Both implementations remain CANDIDATE repairs. UNKNOWN: production incidence, relative runtime cost, alternate observables (interpolation/reprojection), callback purity contracts, optimal hybrid and maintainer intent. Neither is a proof of globally safe caching or a measure of v8 ranking superiority over conventional review (the file-size baseline selected the same file).

## Candidate reusable mathematical obligation

Let `U(x)` be the tile URL and `B(x)` the complete relevant cached behavior, including the loader and tile class. A reuse key must preserve the distinctions of `B`, not just `U`. In the adversary, `U(x)=U(y)` but `B(x)≠B(y)`, falsifying the attempted factorization of observed behavior through URL alone.

**Next decisive experiment.** Study a contract-gated hybrid that reuses source-owned certified invariant cases without invoking callbacks, selectively revalidates per-tile values only under an independently warranted pure-loader/pure-URL contract, and conservatively invalidates unknown cases. Avoid public API growth on deprecated TileImage without maintainer guidance. Separately run a genuinely prospective representation-versus-informed-review baseline; this repair comparison is not that trial.
