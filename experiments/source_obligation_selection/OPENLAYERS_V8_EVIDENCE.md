# MathGraph v8 — OpenLayers dependency-gap trial

**Research boundary:** Advisory source-to-obligation extraction; source-exact bounded behavior replay; not a full browser test or a production failure claim. All pinned source and upstream checks were read-only. MathGraph `main` and OpenLayers upstream remain unchanged.

## Objective and frozen conditions

Find missing input dependencies of cached behavior without hard-coding particular bug types. Compare v7's explicit quotient view to v8's key-versus-cached-behavior dependency view, using an OpenLayers code slice selected before inspecting source contents.

- Repository: `openlayers/openlayers`
- Pin: `e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2` (2026-11-17 UTC)
- Selection: 12 largest JS blobs (1,800–14,000 bytes), `src/ol/` paths matching cache/tile/image/source/layer/reproj/loader, excluding tests/vendor/build.
- Frozen manifest SHA-256: `e7d885e37c4a3fa564ad8cf503125b056dcd3b26c0e2f893a94ecc68e6385efe`
- Frozen v8 scanner SHA-256: `9f08311e2d4d9579f953a4294a0eee038cc38620189c0aa5b9c67e39142a23fe`
- Baseline v7 SHA-256: `dff93dd97a6c75b58e13fd176e2de18cd0c03a3ac5bd3104104e10c6a0805011`
- Source/tool integrity and regression run: https://github.com/metalogiclabs/mathgraph/actions/runs/44264426198
- 12/12 Git blobs checked, 62/62 local Node controls passed in Actions. v7: 0 candidates; v8: 1 candidate. **No independently qualified defect from the scan.**

## Top source-ranked candidate

`src/ol/source/TileImage.js` method `getTileInternal`: cached result creation depends on `pixelRatio` and `projection`, while its cache key derives from source ID/source key/tile Z/X/Y. Candidate location `TileImage.getTileInternal:tileCache|sym:1`; score 82. The first-largest-file control also selects `TileImage.js`; no superiority in selecting the file has been established.

Code evidence:

- `TileImage.js:287–296`: cached hit returns `tileCache.get(cacheKey)`; a miss invokes `createTile_(z,x,y,pixelRatio,projection,key)`.
- `TileImage.js:196–216`: source URL function is passed `pixelRatio` and `projection`.
- `tilecoord.js:71+`: cache key is source UID, source key and Z/X/Y, no pixel ratio.
- `renderer/canvas/TileLayer.js:238–274`: renderer cache also keys on source/tile coordinates, supplying `frameState.pixelRatio` when calling source on a miss.
- `renderer/canvas/TileLayer.js:514–530`: cache clearing on changed projection/source revision, not pixel ratio.
- `Map.js:1138–1150` publicly allows `Map.setPixelRatio`, changes the stored ratio and requests a new render; `Map.js:1789` transfers it into `frameState`.

## Source-exact differential replay (warranted within scope)

- Original pinned source classes; only external `Image` object was stubbed, with no upstream source edits. Run: https://github.com/metalogiclabs/mathgraph/actions/runs/44265255055
- A tile URL function intentionally depends on `pixelRatio`. With one canvas renderer and the same tile coordinates/projection, a frame ratio change 1 → 2 reuses the existing tile and retains `?ratio=1`. A fresh renderer, or direct uncached call, produces `?ratio=2`.
- Earlier internal-method-only replay on pinned source: https://github.com/metalogiclabs/mathgraph/actions/runs/44265050220. This alone would not have established the public renderer path; the later run supersedes that limitation.
- The normal reprojection path uses a configured fixed source pixel ratio (`Tile.js:212–213`); projection changes clear renderer caches. Those are meaningful negative controls, not defects.
- The newer `source/ImageTile.js` is backed by `DataTile` loader options that do not include pixelRatio; the demonstrated path concerns the deprecated `source/TileImage.js` and the shared canvas renderer. Do not generalize it to all tile sources.

## Causal repair check

- In a temporary checkout only, a candidate guard in `CanvasTileLayerRenderer.prepareFrame` clears `tileCache_` (and `sourceTileCache_`) when an existing `renderedPixelRatio` differs from `frameState.pixelRatio`.
- After simulating a completed prior frame (`renderedPixelRatio=1` as done by the real `renderFrame`), the changed-ratio frame builds `?ratio=2`. Same-context repeated requests reuse the cached tile both before and after the transition.
- Source-exact bounded repair controls: https://github.com/metalogiclabs/mathgraph/actions/runs/44265681874
- **Not production-ready:** no full upstream browser/Karma/Vitest regression, independent API-owner adjudication, performance qualification, or source-integration PR. No upstream comment or PR has been posted.

## Research lineage and negative findings

- v8's first Actions run #44264234559 failed during payload extraction because the uploaded delta omitted v5–v7 runtime files. This was a harness packaging failure; the complete frozen payload rerun #44264426198 succeeded with the original v8 SHA.
- Patch harness run #44265616482 failed on a Python newline-escaping error. The guard and test were unchanged after correcting the harness; run #44265681874 passed.
- v7 found 0/12 candidate hotspots in the OpenLayers sample. v8 found 1. The simple largest-file baseline selected the same file as v8, so comparative value in prioritization is **UNKNOWN**.
- The `TileImage` class is marked deprecated. Related but not identical upstream history includes openlayers/openlayers issues #11983 and #11259 on device pixel ratio and caching; do not assert novelty or owner acceptance.

## Epistemic register

- **WARRANTED BOUNDED:** v8 reads exact pinned files, emits one source-linked dependency-gap candidate, native pinned class and canvas renderer reproduce the ratio-dependent cache reuse for constructed frame states, and a one-guard local repair changes that result while retaining same-ratio reuse.
- **REJECTED:** the broad interpretation that all uses of omitted `projection` or `pixelRatio` are defective; projection and fixed-ratio source paths have guards.
- **UNKNOWN:** real deployment incidence, appropriateness of changing an API for a deprecated source, correctness/performance across the wider OpenLayers test suite, and whether v8 beats an informed baseline on new code.
- **CANDIDATE REUSE:** augment the representation with reachable-variable/path constraints and evidence about cache-owner identity, not merely a list of explicit lossy operations.

## Smallest useful next experiment

Run the exact-version upstream targeted browser suite with a regression for `Map.setPixelRatio(1→2)` using a pixel-ratio-sensitive URL tile source, compare patch OFF vs ON, and ask a maintainer whether dynamic ratio changes should invalidate renderer tile caches. Only then decide whether to propose an upstream repair. Separately preregister a second new-source comparison against v8 and strong conventional reviewer/size baselines.
## Later patch artifact and exact application check

The candidate patch is [openlayers_pixelratio_prepareframe_CANDIDATE.patch](https://github.com/metalogiclabs/mathgraph/blob/experiment/ast-obligation-dependency-v8-20261118/experiments/source_obligation_selection/openlayers_pixelratio_prepareframe_CANDIDATE.patch). [Exact-pinned Actions run #44266475409](https://github.com/metalogiclabs/mathgraph/actions/runs/44266475409) passed `git apply --check` against the pinned OpenLayers source, reran the native ratio-transition reproduction, and passed the bounded candidate-repair and same-context reuse controls. This validates only patch applicability and the exercised fixture; full OpenLayers browser/regression qualification and maintainer authorization remain UNKNOWN.


## 2026-11-18 — Exact upstream Chromium browser qualification (WARRANTED BOUNDED)

**Supersedes the earlier “browser suite unrun” limitation** in this record. The independent browser test and the existing candidate patch are preserved on branch `experiment/openlayers-pixelratio-browser-20261118`; no OpenLayers upstream file or MathGraph `main` was changed.

- **Pinned implementation:** `openlayers/openlayers@e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2`; verified `TileImage.js` blob `635368dc621ea80a531adbef9acb2466e3dd22d8`, canvas `TileLayer.js` blob `d33f91592944d322c743f1bf0f950e1bee467938`.
- **Real browser witness:** [new Chromium spec](openlayers_pixelratio_browser_regression.test.js) executes the real public `Map.setPixelRatio(1→2)` path with a controlled pixel-ratio-sensitive `XYZ` URL function and in-memory image loader. Source unmodified: **2/3 tests pass**, with the transition test failing on the exact expected assertion `MATHGRAPH_RATIO_STALE_CACHE_EVIDENCE`. Four cached tile URLs stay at `ratio=1` although the map reports ratio 2; fresh ratio-2 and same-ratio-reuse controls pass.
- **Temporary source patch:** [guard candidate](openlayers_pixelratio_prepareframe_CANDIDATE.patch) applied with `git apply --check` and `git apply` to exact checkout; unchanged new test and three existing upstream Map/TileImage/TileLayer browser specs **107/107 PASS** in Chromium.
- **Complete native browser qualification:** On the same patched checkout, full `npm run test-browser` **175/175 browser files, 3,125/3,125 tests PASS**. See [GitHub Actions run #44277397227](https://github.com/metalogiclabs/mathgraph/actions/runs/44277397227), [artifact #14414913259](https://github.com/metalogiclabs/mathgraph/actions/runs/44277397227/artifacts/14414913259) (`sha256:8807468a29a8021252758d7efdf2c5b40d01771873d8a0921b0f540afde7b46e`); includes baseline log, patched targeted log, patched complete-suite log and diff.
- **Superseded harness failure:** First [run #44276857033](https://github.com/metalogiclabs/mathgraph/actions/runs/44276857033) exited before patch application because shell `errexit` treated the **intentionally failing** baseline regression as fatal. The workflow-only correction then made [#44277072761](https://github.com/metalogiclabs/mathgraph/actions/runs/44277072761) green with 107/107 targeted. The browser test and patch were unchanged.

**Epistemic boundary:** WARRANTED for the pinned source, supported public Map method, constructed but valid ratio-dependent tile URL behavior, and exact Chromium browser-suite compatibility under the candidate patch. **UNKNOWN:** real deployments affected, patch performance/memory impact, correct handling across untested non-browser environments, relevance to newer DataTile-backed source, maintainer's intended compatibility contract, and suitability for upstream integration. A patch compiling and passing a suite does not constitute maintainer acceptance or general certification.

**Representation value:** v8 found this source location prospectively (v7 found none in the frozen 12-file sample), but a simple largest-file baseline also chose the same file; **comparative prioritization superiority remains UNKNOWN**. The next consequential experiment is to evaluate performance/cache churn for a ratio-independent source and obtain maintainer review, then freeze a new blind source trial against an informed conventional-review baseline.


## 2026-11-18 — Cost adversary: ratio-independent URLs (candidate repair tradeoff)

**WARRANTED BOUNDED / negative for patch minimality.** [Pinned original-source Chromium workflow #44278154054](https://github.com/metalogiclabs/mathgraph/actions/runs/44278154054) measured a ratio-independent `XYZ.tileUrlFunction` across public `Map.setPixelRatio(1→2)`. The [source-linked diagnostic test](openlayers_pixelratio_churn_diagnostic.test.js) creates four cached tiles, with a URL function that does not use the ratio:
- Candidate patch **OFF:** four URL-function calls total before and after transition (0 additional); all original tile objects retained.
- Candidate patch **ON:** four calls before and eight total after (+4 extra calls); no original tile objects retained. Both executions pass the diagnostic's structural controls; these counts reflect the constructed scene only, **not measured deployed latency or resource cost**.
- New regression / full suite unchanged in intended behavior: after candidate patch, existing + new Chromium tests **176/176 files, 3,126/3,126 PASS**. [Artifact #14416170928](https://github.com/metalogiclabs/mathgraph/actions/runs/44278154054/artifacts/14416170928), digest `sha256:7dfc8fc35cb60404f83e8b1feb18a3325e2411fe2ed366818f23efcd95eadad9`.

**Interpretation:** Broad renderer cache invalidation is a <b>working safety-oriented candidate</b> but is **REJECTED as proven minimal/performance-neutral**. Invalidation cost when ratios change must be assessed alongside correctness; deduplicating only when source behavior is equivalent may require an explicitly warranted per-source equivalence relation. Do not infer that a function's argument is irrelevant from its signature or that a source without ratio-sensitive URL output has no other ratio-sensitive state. The next cheapest decisive experiment is a selective caching strategy with the same off/on witness, negative controls and full browser suite. Maintainer intent still UNKNOWN; no PR upstream.


## 2026-11-19 — Selective URL-revalidation candidate (WARRANTED BOUNDED; production UNKNOWN)

**Objective:** Improve the previously qualified broad cache invalidation repair without discarding correct cached tile objects on a frame pixel-ratio transition. Preserve the original broad candidate as its own negative baseline. No OpenLayers upstream write, MathGraph `main` write, PR, or maintainer approval.

**Source / change:** The [selective candidate patch](openlayers_pixelratio_selective_CANDIDATE.patch) changes only `src/ol/renderer/canvas/TileLayer.js` against exact `openlayers/openlayers@e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2`. On a changed frame pixel ratio, it compares each existing legacy image tile's stored source URL with a newly computed URL under the current ratio. A tile with unchanged URL remains the same cached object; a changed URL causes only that tile's removal and rebuilding. A conservative full-cache invalidation fallback applies to tile kinds, overridden source methods or reprojection paths not covered by the comparison. This is a **candidate source-specific equivalence check**, not general proof that URL equality establishes all behavioral equivalence.

**Exact-version native Chromium evidence:**
- [Run #44443932949](https://github.com/metalogiclabs/mathgraph/actions/runs/44443932949): source-pinned positive ratio-dependent tile regression and ratio-independent reuse control both PASS; full upstream browser suite **176/176 files, 3,126/3,126 tests PASS**. For four ratio-independent tiles, original code has 4 URL-function calls and retains all original tiles; broad clear has 8 calls and replaces all four; selective has **8 calls but retains all four**. The extra URL computation is real; saved tile construction and reloads are the measured benefit, not zero CPU cost. Artifact [#14491753987](https://github.com/metalogiclabs/mathgraph/actions/runs/44443932949/artifacts/14491753987) digest `sha256:c3f3612e9f01bbb7e63574b04cc83c631e2b4d3c38ee54cbd4f025f9549e1bc7`.
- Stronger mixed control [run #44444697115](https://github.com/metalogiclabs/mathgraph/actions/runs/44444697115): one source, four cached tiles, two URLs depend on ratio and two do not. The unmodified source failed the expected mixed regression; **unchanged selective candidate passed with exactly 2/2 ratio-dependent tiles rebuilt and 2/2 independent tiles preserved**. Full Chromium suite **177/177 files, 3,127/3,127 tests PASS**. Mixed test made 10 URL-function calls for four initial tiles and four revalidations plus two rebuilt tiles. Artifact [#14492553324](https://github.com/metalogiclabs/mathgraph/actions/runs/44444697115/artifacts/14492553324) digest `sha256:48223e5baa8f084c1a7ef98af2dc373a400d7e361720c553dbaa75fc2ca1f533`.
- Exact upstream implementation blob `CanvasTileLayerRenderer TileLayer.js d33f91592944d322c743f1bf0f950e1bee467938`; all GitHub Actions workflows checked source commits and applied candidate only to a temporary upstream checkout. The original ratio-dependent browser baseline still fails as a protected negative control.

**Negative and uncertainty boundaries:** Comparing URL function output executes the function again (possibly with side effects) and accesses legacy tile `src_` internals; unrecognized custom source behavior triggers conservative invalidation. URL equality protects source URL identity under bounded inherited legacy image-tile constructors, but does **not prove full observational equivalence** of arbitrary subclass implementations. The experiments do not establish deployed incidence, benchmark CPU/heap/network savings at realistic scale, hidden geometry/cross-projection behavior, relevance to newer DataTile sources, or maintainer compatibility intent. Selective patch is **CANDIDATE**, not upstream-approved or necessarily optimal.

**Reusable insight:** The right hotspot/repair obligation is not “any omitted input is a bug,” but “a reachable difference omitted by cache identity can change an observed result.” If an observable result can be rechecked cheaply, invalidate only entries whose corresponding output actually differs. The current result strengthens **within-repo repair selection**, not the unresolved claim that MathGraph v8 outperforms a strong conventional-review/LOC baseline in finding the location. **Next experiment:** challenge the conservative method-override/reprojection fallback and evaluate perf costs; then obtain maintainer boundary before upstream publication.


## 2026-11-19 — Typed selective repair v2 (WARRANTED BOUNDED)

**Objective:** Preserve v1's exact-browser selective behavior while honoring source ownership and upstream static-analysis/type boundaries. v1's renderer accessed `TileImage.createTile_`, `TileImage.getTileInternal`, `TileImage.tileClass`, and `ImageTile.src_` across private/protected boundaries. These are not admissible source accesses under OpenLayers' TypeScript checks, even though the browser result was correct. v1 retained as **SUPERSEDED CANDIDATE**; [its failing typecheck #44445661671](https://github.com/metalogiclabs/mathgraph/actions/runs/44445661671) found six exact TS2341/TS2445 errors. Earlier formatter-only failures #44445441136, #44446319258, #44446582191 were harness/style residuals; not browser failures.

**Changed representation boundary:** [typed v2 patch](openlayers_pixelratio_selective_TYPED_v2_CANDIDATE.patch) modifies exact pinned `openlayers/openlayers@e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2` in three files: `src/ol/ImageTile.js` adds a source-URL getter *inside* the owning class; `src/ol/source/TileImage.js` owns the conservative inherited-constructor/URL-equivalence predicate; and `src/ol/renderer/canvas/TileLayer.js` asks that predicate during a frame pixel-ratio change and removes only the mismatching entries. Unrecognized source types, overridden methods and reprojection paths retain conservative invalidation. The v2 candidate adds an internal method/getter and is not yet accepted upstream.

**Final exact-version source-owned qualification:**
- [GitHub Actions #44446776579](https://github.com/metalogiclabs/mathgraph/actions/runs/44446776579) **SUCCESS**: complete `npm run pretest` runs upstream lint, `tsc` and `typecheck-libcheck`; no lint/TypeScript errors. Artifact [#14493491956](https://github.com/metalogiclabs/mathgraph/actions/runs/44446776579/artifacts/14493491956), digest `sha256:027702d9b6a32e6dac9cd125585b2fc221e0f3561f6a00e78756ab58a7f7ebd5`.
- [GitHub Actions #44446776658](https://github.com/metalogiclabs/mathgraph/actions/runs/44446776658) **SUCCESS**: exact pinned source, protected **expected-red** unpatched ratio transition (2 positive controls), green changed-ratio and ratio-independent reuse, mixed-source unpatched expected-red/patch-on-green (**2/2 dependent tiles rebuilt, 2/2 independent retained**), four existing upstream suites 107/107, and full Chromium **177/177 browser files / 3,127/3,127 tests**. Artifact [#14493925943](https://github.com/metalogiclabs/mathgraph/actions/runs/44446776658/artifacts/14493925943), digest `sha256:591627cec6830dc078f1371bf3caeaf5ba3d8163cce4cacf5279068997f067ef`.
- Ratio-independent single-source cost controls still show four initial URL computations plus four revalidation computations (eight total), **all four original tile objects preserved**, no forced reconstruction in the controlled ratio transition. Original and blanket-clear v1 causal controls remain as previous evidence.

**Assessment:** WARRANTED BOUNDED source-exact browser and native lint/type compatibility. **UNKNOWN:** consumer authorization for new internal methods on deprecated legacy source, source-function side effects, arbitrary subclass behavior outside the guarded methods, reprojection/other cache ownership behavior, full performance/memory/network effects, deployed incidence and upstream maintainer acceptance. No OpenLayers upstream write, MathGraph `main` write or external PR. The entire repair sequence is a retrospective within-repo calibration following the prospectively nominated v8 hotspot; it does **not** qualify MathGraph v8's advantage over the strongest conventional-review baseline. **Next highest-leverage experiment:** preregister another codebase/held-out source ranking with fair size and source-aware conventional controls rather than indefinitely tuning this repair.
