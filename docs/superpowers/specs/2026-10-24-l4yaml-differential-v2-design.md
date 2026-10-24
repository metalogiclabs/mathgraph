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
