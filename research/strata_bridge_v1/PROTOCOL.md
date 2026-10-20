# Strata SMT/Lean semantic-boundary replay (2026-10-20)

Status at freeze: RETROSPECTIVE_EXPOSED_SOURCE. Public upstream issue #1488 was already read before this protocol. Never classify as blind transfer, automatic discovery, independently discovered upstream vulnerability, or expert superiority.

## Current objective
Transfer the *structure* from the Aeneas Drop result into another verification family: distinguish source denotation from generated Lean proof goals, identify trusted verifier assumptions, and apply the unchanged MathGraph consequence/withdrawal resolver.

## Pinned sources and witness
- Strata main: 0bbe12d22650dc12dc4adc15249c965ba5ade8e3
- Strata proposed PR #1490 head: 4016549f846065b5cab405fc09cff9a35d13512f
- Lean upstream-pinned v4.31.0
- Public upstream issue: https://github.com/strata-org/Strata/issues/1488
- Proposed patch: https://github.com/strata-org/Strata/pull/1490
- Aeneas lineage: https://github.com/metalogiclabs/mathgraph/actions/runs/39349049595
- MathGraph resolution implementation must remain unchanged: mathgraph_check/warrant_resolution.py

## Acceptance contract frozen before native run
1. At exact original revision, compile Strata.MetaVerifier from genuine upstream source.
2. Separately run a kernel-checked 8-bit oracle: Lean unsigned /0 = 0, SMT smtUDiv /0 = 255, and those two are different.
3. Run the public issue-1488 Lean reproducer; expected proof of False only under the explicit per-theorem _genSMTVCs_tcbBridge extra axiom; demand printed axiom report and absence of sorryAx.
4. At exact patch revision, compile same native target and rerun unchanged arithmetic oracle, then unchanged repro. Expected patch refuses the unsound proof with Lean error; no source repairs or changing repro allowed.
5. Run MathGraph resolver from repository, with no changes to its implementation. Test four distinct evidence withdrawals, exact lost-claim sets, preservation of unrelated claims, restoration, and refusal to promote unqualified cross-boundary equivalence.
6. Compare reported outcomes with separate explicit 8-bit reference-rule proxy using same observed values. A tie means no method advantage and is not an equally informed human evaluation.
7. Archive source hashes, native build logs, outputs, diagnostics, failures and receipts.

## Claims and boundaries
- Any proof of False under the generated bridge axiom demonstrates the trusted axiom's impact, NOT a Lean kernel inconsistency.
- SMT source denotation is authoritative for this pinned Core operand. The signed/unsigned and zero-divisor scope must not be widened to all operators or arbitrary programs.
- Original PR is pre-exposed, so source-disjoint prospective method discovery remains UNKNOWN.
- Withdrawals are LOGICAL from declared MathGraph evidence receipts. No upstream artifact is physically deleted; receipt authenticity depends on the trusted test runner / independent audit.
- A green patch rejection shows this exact bug blocked at a pinned proposed patch. It does not warrant general verified compiler/SMT correspondence.
- Refuted finite meaning preservation remains distinct from unavailable warrant for universal preservation.

## Stop conditions
Fail original on build or absent exposed proof. Fail native assurance if extra bridge axiom absent or sorryAx used. Fail patch qualification if build fails or unchanged reproduction still succeeds. Fail resolver on any overbroad/nonselective invalidation or un-restored closure. Do not re-label failures as green or tune fixture to this case after results.
