> **SUPERSEDED — historical research snapshot.** This document predates recovery of the original Crystal comparator, the RealityGraph cross-repository replay, and subsequent Lean qualification. Do not use its UNKNOWN table as the current state. See [evidence-qualified completion](foundation_evidence_qualified_completion_2026-10-11.md) and the latest PR description.\n\n# Foundation closeout decision — evidence-limited, 2026-10-11

## Objective
Determine whether the candidate universal Consequence Envelope v0 should become MathGraph's canonical transport, and whether all proposed foundation experiments can be completed from available evidence.

## Critical existing architectural evidence
The merged product audit (`docs/mathgraph_full_product_audit_2026-10-11.md`) explicitly states: **no normative MGSO implementation/test vectors in the current tree**; Crystal/MGSO is historical and experimental, not the deployed P0 record format. The public protocol page agrees. The historical `mathgraph-crystal-v0` specification defines an opaque canonical-byte envelope and says it creates no warrant.

## Replayed evidence
- 31/31 stateful source-bound and finite consumer checks: https://github.com/metalogiclabs/mathgraph/actions/runs/38113183557
- 38/38 including independent Python implementation of specified MGSO byte encoding: https://github.com/metalogiclabs/mathgraph/actions/runs/38113494386
- 38/38 plus 7/7 real two-domain campaign: https://github.com/metalogiclabs/mathgraph/actions/runs/38113635038
- Exact archived JPL V1/V2 ZIP hashes verified, JPL source-check release builder replayed, existing independent finite consumer replayed, MGSO byte transport round-tripped, receiver oracle checked finite reuse and ablation.
- Real-domain results remain distinct; the dependency invalidation demonstration uses a synthetic support graph.

## Decisions by obligation
1. **Source byte identity and preservation**: WARRANTED_BOUNDED for the tested Python MGSO codec and payloads.
2. **Native source semantic interpretation**: WARRANTED_BOUNDED by existing JPL and finite consumers, not by MGSO.
3. **Transport creates no warrant**: protected by tested fail-closed controls.
4. **Canonical MGSO deployment**: UNKNOWN; no normative production MGSO runtime and no independently pinned original Crystal binary comparator found in current main audit. A Python implementation matching a spec is not original-Crystal cross-implementation qualification.
5. **Cross-domain semantic equivalence**: NOT_CLAIMED; JPL and finite refinement have different meaning and must never be declared equivalent.
6. **Real certified dependency edge/revocation/alternate proof**: UNKNOWN; synthetic support graph is insufficient.
7. **WebArena negative replay**: UNKNOWN; current suite preserves reported strong-baseline tie, does not rerun the environment.
8. **Causal cross-family acquisition and costed compounding**: UNKNOWN; finite reuse and ablation do not demonstrate new-family growth or economic win.
9. **External independently operated adoption**: UNKNOWN; no third-party consumption evidence.
10. **Universal sufficiency of one Unit ontology**: UNKNOWN; cannot be established by a finite test suite.

## Architectural recommendation
Do **not** promote the fixed-kind Consequence Envelope v0 as canonical or require it in the public API. Keep current Check/Resolve/Capability contracts normative within their own bounded release profiles. Use MGSO as an **optional experimental opaque-byte transport candidate**; preserve unknown types, domain authority, original artifacts, and policy axes. The first independent real adapter requiring an MGSO interface should determine whether it is necessary. This is a no-new-foundation-format decision, not a claim of universal sufficiency.

## Remaining decisive gates, with falsifiers
A. Pin the historical original Crystal implementation and build identical byte vectors. Reject interoperability on any identity/encoding mismatch.
B. Obtain a real, policy-qualified dependency graph with two independent evidence paths; revoke one and demonstrate precise retention, invalidation, and requalification.
C. Obtain executable WebArena strong stateless and ledger comparators; replay matched held-out tasks with total-cost accounting. A tie is not compounding.
D. Have an independent organization or separately maintained consumer import and requalify without producer private access.

Do not invent evidence to close A–D. Preserve UNKNOWN until actual artifacts and independent verifiers exist.

## Release
PR #157 remains draft and unmerged. No production changes, existing records, registries or trust policies are authorized by this decision.
