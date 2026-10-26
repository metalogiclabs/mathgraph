# JPL L4YAML — independent graph-composition assurance handoff (2026-10-26)

**Audience:** Internal MathGraph / prospective NFM 2027 coauthor evidence. Not sent to JPL. Not an endorsement by Nicolas Rouquette, JPL, Caltech or NASA.

## Upgrade: conditional event-to-graph theorem (26 October, later proof run)

**WARRANTED formal sublanguage correspondence:** The native Lean 4.35 compiler checked `graphTraceCheck_agrees_with_JPL` at MathGraph commit `1106cf3965da59b017333e31c55a1a81a52d5a5f`, importing **JPL's actual** `SerializationWellFormed.Event`, `Env`, `AliasAllowed` and `checkFrom` at immutable `L4YAML@4458c26e9a69411eadc1b35a4eea6968b1eb7f28`. This establishes, for an *arbitrary list of explicit anchor events* consisting of document begins/ends, `defineAnchor(name,nodeId)`, and `useAlias(name)`, that if JPL's environment's registered-name list corresponds to the names in MathGraph's graph state, then the graph checker agrees with JPL's independent trace well-formedness checker after projecting away the node IDs. The helper `first_match_some_iff` proves alias-target existence iff the name is in the registered-name list. The theorem handles repeated anchor names and document resets by induction over every fragment event; it is not limited to fixed test inputs. The actual graph composer additionally retains already checked `started_anchor_visible`, `allocation_is_fresh`, and native reference-identity tests.

**Current combined green evidence:** [Actions 40263571041](https://github.com/metalogiclabs/mathgraph/actions/runs/40263571041) and [artifact 12624694385](https://github.com/metalogiclabs/mathgraph/actions/runs/40263571041/artifacts/12624694385). Existing 532/532 graph topology, 532/532 value agreement, genuine cyclic sequence and mapping self-ID, nested and sequential rebinding, and three invalid-alias refusals all remained green. The exact source-native run completed with **no failing step**. Original JPL source unchanged.

**The essential counterevidence:** On 26 October, Nicolas merged [L4YAML PR #119](https://github.com/nasa-jpl/L4YAML/pull/119), formally **refuting unrestricted `TraceOf` uniqueness** with two block/document ambiguity pairs. A subsequent open [PR #120](https://github.com/nasa-jpl/L4YAML/pull/120) addresses the `[173]` scalar-indent tail; no source-wide unique trace should be assumed. MathGraph's theorem therefore **requires a selected, authenticated event trace** and is restricted to anchor/name events. It does not claim source→unique trace, that the graph IDs supplied to the trace arise from the real source positions, that JPL's entire parser agrees with those events, or that the tag-handle fragment is covered. These remain **UNKNOWN**, not consequences of a passing graph test.

**Open proof gap after this milestone:** (1) trace provenance/selection from actual scanner+parser, (2) correspondence between event `defineAnchor(name,nodeId)` and the graph composer's real node-start ID assignment (not merely an externally supplied ID), (3) expansion to tag/flow/block events with ambiguity exclusions, (4) independent native audit at each newer JPL commit rather than transplanting the old full-commit warrant. No source-wide YAML completeness or NASA/JPL endorsement claim is authorized.

**Preserved historical RED:** [CI 40263167834](https://github.com/metalogiclabs/mathgraph/actions/runs/40263167834) had an unsolved Lean proof goal requiring reversed inequality and output-linter cleanup; [green 40263571041](https://github.com/metalogiclabs/mathgraph/actions/runs/40263571041) fixed the proof without changing the acceptance oracle. Neither was a JPL upstream failure.

## Verdict

- **WARRANTED, bounded native result:** On untouched `nasa-jpl/L4YAML@4458c26e9a69411eadc1b35a4eea6968b1eb7f28` with Lean **4.35.0**, a MathGraph-owned ID-addressed graph composer, using **both native raw parser pipelines**, agrees with independent `ruamel.yaml==0.18.17` graph topology in **532/532 selected acyclic inputs** and with their independent typed JSON value oracle in **532/532**. Inputs: 180 repeated-anchor variants (12 families) and 352 ordinary examples. No graph-path divergences. [Green native CI 40255413163](https://github.com/metalogiclabs/mathgraph/actions/runs/40255413163); [complete artifact 12621839149](https://github.com/metalogiclabs/mathgraph/actions/runs/40255413163/artifacts/12621839149); tested MathGraph code `8c47210e0bbd26b84cddba4d8cd69ccfd7d4b215`.
- **WARRANTED, targeted reference identity:** `&x [*x]` produces one sequence node with its child edge equal to its own node ID; `&x {a: *x}` similarly contains a mapping value edge to its own node ID. For `[&x [&x 1], *x]`, the trailing alias is the ID of the *inner scalar*, not the enclosing sequence. Sequential rebinding preserves both old and new alias identities. Independent `ruamel.yaml` graph nodes and a separate `PyYAML==6.0.3` self-cycle check corroborate the bounded identities. `[*x]`, a missing alias inside a cycle, and cross-document alias reuse are all refused by the source-native parsers.
- **WARRANTED, small Lean proof obligations in the actual composer:** `started_anchor_visible` proves a new binding is immediately available to descendants, even before child traversal; `allocation_is_fresh` proves the reserved node ID is the pre-insertion graph length. Both compile in the same successful Lean 4.35 source-native run. These facts do **not** constitute a general correspondence theorem for a complete YAML implementation.
- **UNKNOWN:** proof that arbitrary YAML documents have matching graph semantics; complete parser/serialization round-trip; exotic mapping-key semantics, resource bounds, generated-code correspondence, downstream scientific correctness, deployment suitability, and release permission.

## Concrete before/after result

The original JPL `YamlDocument.compose` performs collection-anchor registration after its children. A minimal distinguishing case is `[&x [&x 1], *x]`: JPL's existing JSON path produces `[[1],[1]]` while the independently composed YAML graph projects to `[[1],1]`. All **105** observed mismatches are members of seven nested-rebinding families, 15 variants each.

A prior MathGraph-owned *tree-valued* event-time experiment changed the 532-case agreement from **427/532 to 532/532** with zero regressions ([green CI 40252659793](https://github.com/metalogiclabs/mathgraph/actions/runs/40252659793)), but could not preserve cyclic node identity.

This new graph-level experiment allocates IDs at the event start, records anchor name → node ID using newest-first lookup, and represents aliases as existing-ID edges. It uses the *original* JPL `parseYamlRaw` / `parseYamlRawIx` trees, not a patched JPL parser, and reproduces both acyclic value agreement and selected cyclic graph identity. It is a **MathGraph candidate repair**, not an upstream change.

## Test boundary and independent assurance

1. Checkout only immutable upstream commit `4458c26e9a69411eadc1b35a4eea6968b1eb7f28` and check clean tracked files; build original source with Lean 4.35.0.
2. Acquire byte-hashed wheels `ruamel.yaml==0.18.17` and `PyYAML==6.0.3`; reconstruct exactly the previous independently qualified oracle and 532 input strings.
3. Execute `GraphComposeProbe.lean` using both original native parsing pipelines; reject non-JSON output and inconsistent input order, source paths, or graph stages.
4. Compare **graph topology by canonical preorder node IDs and backedges**, separately from the typed JSON value projection. Require both path outputs to agree. Explicitly verify 7 reference/refusal controls.
5. Retain every input, graph, oracle manifest, check report and code digest in the GitHub Actions artifact.

**Reproducibility location:** [GraphComposeProbe.lean](https://github.com/metalogiclabs/mathgraph/blob/8c47210e0bbd26b84cddba4d8cd69ccfd7d4b215/research/l4yaml_semantic_diff_v2/GraphComposeProbe.lean) · [independent graph_comparison.py](https://github.com/metalogiclabs/mathgraph/blob/8c47210e0bbd26b84cddba4d8cd69ccfd7d4b215/research/l4yaml_semantic_diff_v2/graph_comparison.py) · [source-native CI](https://github.com/metalogiclabs/mathgraph/blob/8c47210e0bbd26b84cddba4d8cd69ccfd7d4b215/.github/workflows/mathgraph-check-l4yaml-graph-identity.yml).

**Historical negatives retained:** [first red harness 40254125559](https://github.com/metalogiclabs/mathgraph/actions/runs/40254125559) (`toJson` namespace issue); [second red harness 40254365428](https://github.com/metalogiclabs/mathgraph/actions/runs/40254365428) (cross-document JSONL escape); [third red harness 40255129035](https://github.com/metalogiclabs/mathgraph/actions/runs/40255129035) (Lean `simp` linter warning contaminated strict JSONL). The third actually compiled the new Lean theorem; the warning was removed before the final green run. None of these failures implicates JPL source.

**Freshness:** After this pinned replay, Nicolas's active branch advanced to `cf3e3607a3962cbfff4673d98c37ef54c5886877`. Independent blob comparisons show `Spec/Types.lean`, `Parser/State.lean`, `Parser/Composition.lean`, `Parser/IndexedComposition.lean`, and `Output/Json.lean` are byte-identical to the tested revision, but this does **not** substitute for a new native CI replay on `cf3e3607`; the exact-revision warrant stays at `4458c26e`.

## NFM 2027 claim recommendation

> A source-pinned independent audit identified 105 related alias-rebinding discrepancies in a finite YAML differential corpus. A separately implemented event-time graph composer, tested against the unchanged Lean parser and independent YAML graph oracles, resolved the finite corpus and preserved selected cyclic-reference identity. The audit distinguishes source-level proof/acceptance, graph composition, and the remaining universal correctness obligations.

Do not say: "L4YAML corrected upstream," "fully YAML-compliant," "all graph semantics formally proved," "JPL accepts MathGraph Check," or "NASA endorsed this result."

## Next residual, if warranted by the manuscript

The cheapest consequential proof goal is to connect JPL's emerging `TraceOf`/event sequence with the experimental node-ID model via a stated precondition (well-formed, unique trace; supported YAML fragment). Establish invariant preservation and alias-target correspondence without relying on JSON value equality. The current tiny Lean lemmas are ingredients, not that full theorem.

**No email, issue, PR, review request or modification to the JPL repositories was made.**
