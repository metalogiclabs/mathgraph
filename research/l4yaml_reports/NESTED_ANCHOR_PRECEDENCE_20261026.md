# Nested anchor precedence — independent source-native triage (2026-10-26)

**Status:** bounded differential WARRANTED; source-level causal explanation CANDIDATE; repair UNKNOWN; full YAML correctness UNKNOWN; release authority NOT_AUTHORIZED.

## Promotion — successful source-native intervention (2026-10-26)

**WARRANTED (finite native experiment):** A MathGraph-owned Lean `resolveStart` counterfactual, applied to the *unchanged native JPL raw parser output* for both legacy and indexed pipelines at `L4YAML@264e050653cb6f39c1de0e752262819e84cbaf45`, changes the 532-case value-oracle agreement from **427/532 to 532/532**. Exactly **105 repairs, zero regressions**; each of seven nested repeated-anchor families improves 15/15, five control anchor families retain their 75/75 agreement, all 352 ordinary controls stay green. The original source was not patched. [Green CI 40252659793](https://github.com/metalogiclabs/mathgraph/actions/runs/40252659793) at owned code commit `ab79137b2f7fd4dd22ec0fbe7d9678e64619fdbc`; [artifact 12620869167](https://github.com/metalogiclabs/mathgraph/actions/runs/40252659793/artifacts/12620869167) contains both complete 532-case native logs, oracle manifests, family report and 4 alias/cycle controls.

**Mechanism:** the experimental Compose inserts a collection's raw anchor binding into an ordered environment *at the start of the collection* instead of after recursively composing its children. Since this single intervention explains all seven previously failing families, the postorder/preorder cause is supported by an actual source-native intervention (stronger than a source-reading conjecture). The alternative algorithm is still an **experimental CANDIDATE**, not a proved general equivalence or merged JPL repair.

**Separate REFUSAL / UNKNOWN:** cycles remain unrepresented as faithful graph identities. For `&x [*x]`, unchanged JPL JSON is `[null]` and the experimental JSON is `[[null]]`; for `&x {a: *x}`, unchanged JSON is `{"a":null}` and experimental JSON is `{"a":{"a":null}}`. Both accept the input syntactically; neither serialized tree establishes a real cyclic graph. External PyYAML creates actual object-identity cycles. The alias `[*x]` and cross-document `---\\n&x 1\\n---\\n*x\\n` are rejected by both native pipelines and both compositions. **No graph-identity, full YAML conformance, theorem or release warrant is promoted.**

**Preserved failed harness iterations:** [run 40252118754](https://github.com/metalogiclabs/mathgraph/actions/runs/40252118754) failed because executable `main` was namespace-scoped; [run 40252426617](https://github.com/metalogiclabs/mathgraph/actions/runs/40252426617) failed because interpreter `meta import` declarations were missing. These are experiment-harness failures, not source claims. Both fixed before the green native result.

**Next cheapest consequential experiment:** a minimal, ID-addressed graph Compose for self-reference and rebinding, independent of upstream, together with a round-trip graph-identity checker and an explicit acyclic projection; validate equivalence on the 532 cases and constructively verify `&x [*x]` / `&x {a: *x}` point to their own node IDs. Distinguish actual graph-node identity from JSON value comparisons. No upstream write, PR, comment, or contact with Nicolas.

## Objective and immutable evidence

Determine whether the 105/532 remaining YAML oracle disagreements are heterogeneous defects or one isolatable residual, without modifying JPL's source.

- Owned checker: [MathGraph PR #202](https://github.com/metalogiclabs/mathgraph/pull/202), [commit 709429d9](https://github.com/metalogiclabs/mathgraph/commit/709429d9faee71f71f5bca532154ea3c57619444).
- Immutable L4YAML baseline: `82cdb78e8909f25d9079d9bb05ed7c6f508ee95c`.
- Immutable L4YAML candidate: `264e050653cb6f39c1de0e752262819e84cbaf45` (JPL PR #115 merged).
- [Successful two-revision source-native run](https://github.com/metalogiclabs/mathgraph/actions/runs/40250188502), [artifact 12620785173](https://github.com/metalogiclabs/mathgraph/actions/runs/40250188502/artifacts/12620785173); 88/88 targeted Python tests, both Lean builds, 8/8 typed-schema controls for each revision, and independent wheel-qualified ruamel.yaml/PyYAML oracle.
- [Earlier successful run at previous integration head](https://github.com/metalogiclabs/mathgraph/actions/runs/40250000613), [artifact 12619469212](https://github.com/metalogiclabs/mathgraph/actions/runs/40250000613/artifacts/12619469212).
- Historical intentional RED witness: [run 40249383652](https://github.com/metalogiclabs/mathgraph/actions/runs/40249383652). Superseded acceptance expectation is retained, not treated as a parser failure.

## Machine-observed partition

The retained 180-case anchor population has 12 families, 15 name/value variants per family. Seven families have **15/15 oracle mismatches each**, on both source revisions: `nested_sequence`, `nested_mapping`, `deep_nested`, `internal_alias_external`, `two_outer_aliases`, `mapping_internal_alias`, `mapping_outer_sibling`.

Five control families have **15/15 agreements each**: `ordinary_rebinding`, `sibling_after_nested`, `nested_siblings`, `ordinary_simple`, `plain_without_alias`. All 352 ordinary YAML cases agree. Legacy and indexed L4YAML native paths agree on all 532. Thus 105 disagreements are localized to one interacting family, not 105 independent bugs.

**Smallest separating observed witness (acyclic):** `[&a [&a 1], *a]` → independent YAML 1.2 oracle `[[1],1]`; both native L4YAML JSON paths `[[1],[1]]`. The name-renamed `[&x [&x 1], *x]` gives the same difference. Positive controls: `[&x 1, *x, &x 9, *x]` → `[1,1,9,9]` in both; `[&x [&x 1], &x 9, *x]` → `[[1],9,9]` in both.

## Causal hypothesis and boundary

[YAML 1.2.2 §3.2.2.2](https://spec.yaml.io/main/spec/1.2.2/) and §7.1 bind an alias to the most recent *preceding anchor event*; a collection's anchor occurs at its start, before its child anchors.

In pinned [`L4YAML/Spec/Types.lean`](https://github.com/nasa-jpl/L4YAML/blob/264e050653cb6f39c1de0e752262819e84cbaf45/L4YAML/Spec/Types.lean), `YamlValue.resolveAliasesOrdered` recursively resolves collection children first, then pushes the collection anchor into the environment. On the minimal witness, the event-order model therefore predicts `1` but postorder binding predicts `[1]`. The observed native outputs match the latter. This establishes a **candidate explanation**, not a verified repair or universal theorem.

Important separation: [current `TokenParser.parseNode`](https://github.com/nasa-jpl/L4YAML/blob/264e050653cb6f39c1de0e752262819e84cbaf45/L4YAML/Parser/TokenParser.lean) checks declared anchors and accepts self-reference as YAML syntax. The later `YamlDocument.compose` representation step and its value-resolution semantics are independent obligations. A passing syntax/alias declaration guard must **not** be taken as proof of faithful graph composition.

A local independent artifact re-triage reproduced exactly 105 = 7 × 15 and passed fail-closed negative controls for a tampered native log and a substituted source commit. The diagnostic script is locally available from this investigation; it is **not** yet a separately CI-qualified upstream repair.

## Next cheapest decisive experiment

Use the same pinned source and exact two external oracles. On a **Metalogic-owned experimental copy only**, make one bounded interpreter change: install the collection anchor as an event-time declaration before traversing children, while deferring its value materialization / preserving possible self-cycles. Replay the 180 anchor cases plus 352 ordinary controls and both implementations. Accept a promotion only if all seven failing families change to oracle agreement, five positive-control families retain agreement, `&x [*x]` preserves true graph identity (not just parser acceptance), and undefined/cross-document aliases remain rejected. Any partial repair or new disagreement stays CANDIDATE / UNKNOWN. Do not touch, notify, or imply endorsement by JPL/Nicolas.

**Lineage:** the original September completion-time model is WARRANTED only for its historical pin, SUPERSEDED for current parsing; the October 18 JPL declaration repair addresses parse-time legality but not demonstrated graph-composition correctness; PR #115 addresses a separate proof carrier. Never conflate these.
