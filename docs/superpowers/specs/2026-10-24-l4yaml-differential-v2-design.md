# Source-native L4YAML differential V2 design

## Intent

Extend MathGraph Check from 13 handpicked anchor witnesses to a deterministic, independently replayable 532-input acyclic YAML differential suite on each immutable upstream integration SHA. Use this to distinguish the known repeated-anchor residual from the unaffected ordinary Core YAML envelope, without inflating template variants into independent bug counts.

## Approaches and choice

1. **Chosen:** small deterministic template grammar, independent pinned ruamel.yaml 0.18.17 oracle, dynamic Lean 4.35.0 native runner, strict exact-source JSONL qualification; append results to existing owned CI artifact. It is inexpensive, replayable, and reuses the qualified 13-case harness.
2. Random fuzzing: broader discovery potential but weak replay identity and expensive minimization without a locked grammar. Defer until the structured suite is qualified.
3. Prove whole-parser YAML conformance: vastly stronger ambition but not supported by the current source proof obligations; do not represent native comparisons as theorems.

## Contract

- Generate a frozen grammar of 180 anchor-interaction inputs (12 families × 3 names × 5 values) and 352 ordinary Core YAML inputs (ten shapes from three offset patterns × 12 scalars, deduplicated, plus 16 specials).
- Normalize one independent ruamel.yaml 1.2 value per input; additionally corroborate the **352 ordinary cases only** against source-byte-pinned PyYAML 6.0.3. PyYAML's duplicate-anchor refusal means it is not a second reference for those 180 cases. Reject oracle errors, duplicate inputs and malformed/incomplete native records; record cross-pipeline disagreement without hiding it. Keep all observed mismatches, not only familiar cases.
- Require source checkout HEAD equals the supplied 40-hex commit, toolchain 4.35.0, clean tracked files, hashes of critical native files, SHA-256 of input manifest/native results/probe, pinned ruamel wheel and installed composer, and pinned PyYAML wheel and installed constructor/loader bytes. Source changes require new native replay.
- Classify value mismatches separately by template family; keep name-renaming invariance checks limited to families in which names are anchors. Current anticipated native reading is 105/180 mismatch on known anchor interactions, 0/352 mismatch in ordinary cases, 0 legacy/indexed differences, but these are observations to verify, not fixed pass conditions for future candidates.
- Keep decision permission `NOT_AUTHORIZED`, universal YAML proof `UNKNOWN`, and leave NASA/JPL source untouched.

## Acceptance

Independent owned Actions run, raw logs/oracles/strict verifier/report as artifacts, adversarial verifier tests, and a research OS checkpoint with explicit source lineage. No new GitHub App installation, upstream PR or message.

## Prospective PR #89 source transition and typed-schema retention (extension)

The upstream integration branch has not yet advanced. Prospective PR #89 at
`364a80d4f6790175e06e29c59708da3b50c20049` is instead one commit beyond
our pinned baseline `82cdb78e8909f25d9079d9bb05ed7c6f508ee95c` and changes
scanner behavior. The cheapest decisive cross-revision qualification is two
isolated clean native builds, running the *same* 532-source grammar plus eight
typed-schema controls on both, and 19 source-derived scanner-acceptance inputs
from PR #89's guard exhibit. A source-level inference or a downstream Python
library's acceptance is not a substitute for a native observation.

The candidate has eleven expected accept→refuse changes and eight retained
acceptance controls across both native parser implementations. Independently
qualified ruamel.yaml and PyYAML disagree on eleven of the nineteen flow
inputs; retain every disagreement rather than manufacturing YAML 1.2
specification authority from parser consensus. The source transition is
bounded behavioral evidence of a prospective PR, **not** a merged upstream
repair, universal compliance proof, production authority or JPL endorsement.
The 532-case anchor discrepancy must be carried forward, even if scanner
behavior improves. The eight `parseTyped` scalar-style controls preserve an
already-correct behavior distinct from the still-incorrect anchor family.

The paired CI workflow uses exact known source SHAs for its historical
comparison, plus an optional future immutable candidate input. Ongoing
integration-branch monitoring remains separate and must requalify any new SHA.
