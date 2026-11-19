# AST v6 OpenLayers prospective holdout — bounded negative result

Status: **REJECTED as a defect hypothesis in the native tested queue domain**;
**UNKNOWN** outside that domain. No change or repair is authorized.

## Pre-source boundary and provenance

- The original roster and four-arm ranking protocol were frozen in a Notion
  `PRE-SOURCE FREEZE` checkpoint before the OpenLayers source blobs were opened.
  Exact canonical manifest SHA-256: `94909242606f950c4cdbabe8920ec100be67c64fa7f3f1eaa1fa3f0f7e074c32`.
- Original local-only preregistration/runner commits were lost on transient
  scratch reclamation; **do not cite them as durable GitHub evidence**. The
  metadata-only selection was regenerated and its full manifest digest matched
  the earlier freeze. The orchestration runner was reconstructed after source
  checkout, before examining any of the source text or rankings. Its scoring
  rules were the frozen ones; its own bytes were **not** preregistered.
- Unchanged scanners: v5 SHA-256 `7e38038012ce147372d30b435b9e8e5fb6833b5bc92d892bb6373523dfba1743`;
  v6 SHA-256 `a21b1309c144d774c107bc60625ca48742fe5a7706e5a7d0cb21a43efcea9807`.
- Target: `openlayers/openlayers@e80993fdb36a791a3a705d9c6d9ec1dc9d45b5a2`.
  All 71 selected JS files had the exact frozen Git blob SHA-1 and byte count;
  zero parse-diagnostic files; zero scanner failures. The complete raw report
  was generated outside the repository with SHA-256
  `412d37102890f3dedc8933c36d086f496aee07c3e82110bf82dbc098b7e05619`.
- Selection-description caveat: the metadata-only predicate also included
  `src/ol/source.js` and `src/ol/tilegrid.js` because their third path segment
  matched a selected subtree name. The **frozen 71-file roster**, not a repaired
  post hoc interpretation of the prose, governs this test.

## Frozen arm comparison

Three **unique files** were allowed per arm; each AST arm emitted only one
unique candidate file (two correlated `elements` and `priorities` hotspots).

| Arm | Selected files in score order | Outcome |
| --- | --- | --- |
| AST v6 consumer demand | `structs/PriorityQueue.js` (129; `UNKNOWN_CONSUMER`, +0) | Bounded false lead |
| AST v5 unchanged | `structs/PriorityQueue.js` (129) | Same bounded false lead; **tie** |
| Raw file size | `source/GeoZarr.js` (83,168 B); `source/GeoTIFF.js` (43,428 B); `source/Vector.js` (42,859 B) | No admitted consequential defect; **UNKNOWN** |
| Lexical tokens | `source/GeoZarr.js` (62); `renderer/canvas/TileLayer.js` (53); `renderer/webgl/TileLayerBase.js` (41) | No admitted consequential defect; **UNKNOWN** |

The review union contained six files, and every arm's selected files were
available for the same source/contract review. Specific observations:

1. **`structs/PriorityQueue.js`**: `getParentIndex_(index)` computes
   `(index - 1) >> 1` (line 146). The scanner propagates this intentional
   many-child-to-one-parent operation into `siftDown_` and calls array access
   at lines 222–236 a strong representation loss. The parent value controls
   heap navigation; it is **not a cache key replacing two distinct children**.
   The original OpenLayers node test expresses the ascending-priority dequeue
   contract and reprioritization. Our independent array-sort oracle passed:
   two distinct children sharing parent 0; 24 seeded insert/dequeue sequences
   of 97 distinct elements each; and a 90-element reprioritization with DROP.
   Native test scope does not prove arbitrary queue behavior or all caller
   obligations. **Defect hypothesis rejected within tested domain**, not a
   verified theorem of full implementation correctness.
2. **`source/GeoZarr.js`**: `updateDimensions` validates integer selections,
   resolves them before assigning and keys tiles by serialized resolved
   selection (around lines 960–1015). Source evidence of intentional selection
   distinctions, but no independent native behavioral oracle here: **UNKNOWN**.
3. **`source/GeoTIFF.js`**: tile loading rounds source pixel windows and
   explicitly reads samples/masks (around lines 979–1070). No separately
   established violation or behavioral witness: **UNKNOWN**.
4. **`source/Vector.js`**: the public `getFeatureById` documentation explicitly
   equates numeric `2` with string `'2'` (around lines 895–910), and
   `addToIndex_` stringifies feature IDs (around lines 420–450). This is a
   *declared* equivalence, not evidence of accidental identifier collision;
   broader behavior remains **UNKNOWN**.
5. **`renderer/canvas/TileLayer.js`**: `getOrCreateTile` keys a cache from
   source, its key, and `z/x/y` around lines 237–277. No native violation
   established: **UNKNOWN**.
6. **`renderer/webgl/TileLayerBase.js`**: `getCacheKey` constructs a key from
   source identity, source revision key and tile coordinate around line 147;
   the enqueue loop uses that key around lines 370–410. No native violation
   established: **UNKNOWN**.

## Interpretation and next decisive experiment

- This sample gives **no measured v6 advantage over v5**, nor a justified
  superiority claim over size/lexical baselines. A false lead in the only AST
  file is not evidence that no bugs exist in the 71-file slice.
- The apparent recurring structure is **role-sensitive quotienting**: mapping
  two children to one parent is valid for heap navigation, but conflating two
  distinct cache identities can be invalid if a consumer needs the distinction.
  This is a **CANDIDATE** general law, not a verified finding.
- Cheapest next independent check: freeze a paired controlled fixture with
  identical many-to-one arithmetic but different sinks (parent navigation vs
  keyed storage), an independent contract and native negative control. Evaluate
  a proposed role-aware classification against old false positives and a fresh
  withheld source sample. Do **not** tune v6 on this opened holdout and claim
  prospective improvement.

## Reproduction boundary

Using the manifest and runner in this directory, the unchanged archived
scanners from the fixed v5/v6 payloads, and the exact OpenLayers source commit:

```sh
node experiments/source_obligation_selection/run_v6_blind_trial.js \
  experiments/source_obligation_selection/openlayers_v6_preregistered.json \
  /path/to/pinned-openlayers-checkout /path/to/pinned-scanner-directory trial.json
OPENLAYERS_SOURCE_ROOT=/path/to/pinned-openlayers-checkout \
  node --test tests/openlayers_priority_queue_oracle.test.mjs
node --test tests/ast_v6_blind_trial.test.js
```

The runner refuses a mismatched checkout, scanner digest, file count, byte
count, file SHA-1, duplicate entry or unsafe manifest path. Its output remains
`CANDIDATE_ONLY`/`UNKNOWN`/`change_permission:false`; the bounded native
review above is separate from automated discovery.
