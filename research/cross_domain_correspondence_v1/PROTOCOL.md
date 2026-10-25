# Cross-domain semantic correspondence protocol V1 (frozen candidate)

Status: **CANDIDATE — not yet qualified for native cross-domain transfer**. Frozen 2026-10-19.

## Objective
Determine whether one unchanged evidence-admission protocol can classify semantic preservation for two independently verified, heterogeneous native systems: PKC SysML→Lean and L4YAML typed value→YAML.

This is a *generic evidence protocol*, **not** a universal semantic decision procedure. Native, independently justified adapters construct correspondence witnesses.

## Pinned baseline authorities
- PKC V5: JPL source `e0deb453e05ffa63297d9704ceb47d0855193824`; OpenSysML v0.9.1; experimental reproduction https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785 ; SHA-256 raw archive `8546dfc16783f8243329883e12b7a11f49b6d0c7a3634aaa5293e6c32613cbc6`.
- L4YAML: source `fdef03caf19e8862792034793da11020b39d6110`, Lean 4.34; original RED https://github.com/metalogiclabs/mathgraph/actions/runs/39183206058 ; independent prospective verifier https://github.com/metalogiclabs/mathgraph/pull/169 .
- Source repos are NOT modified. A present-day HEAD is not implicitly covered by either pinned result.

## Frozen interface
A claim is `(domain, source_rev, requirement_id, relation_id, subject_digest, evidence_refs, premises, verdict)`.

The domain-specific adapter must independently furnish a witness checked by an identified verifier for a **declared relation**, or a counterexample checked against that same declared relation. Textual similarity is not an acceptable witness for arbitrary propositions.

Decision rules, applied identically in both domains:
1. Missing relation, ambiguous interpretation, unpinned authority, unverifiable evidence, or unverified witness => **UNKNOWN** (no promotion).
2. Independently checked counterexample to the declared correspondence => **REJECTED_BOUNDED** for that specific subject and relation.
3. Independently checked correspondence witness, pinned authorities and satisfied premises => **WARRANTED_BOUNDED**.
4. Any changed or withdrawn authority/premise/verifier invalidates the dependent warrant pending replay; unaffected claims remain unchanged.
5. Conflicting valid witness and counterexample => **UNKNOWN_CONFLICT**, requiring adjudication; never silently prefer positive evidence.
6. No verdict licenses the statement that arbitrary intended meaning is preserved. Promotion to **REUSABLE_BOUNDED** requires both native adapters and withdrawal controls passing with this protocol unchanged.

## Preregistered challenges
| ID | Domain | challenge | expected protocol decision | authority |
|---|---|---|---|---|
| P1 | PKC | verified declaration with no asserted optional statement | WARRANTED_BOUNDED *only for declaration validity* | PKC V5 |
| P2 | PKC | valid declaration plus `statement = "False"` presented as proved | REJECTED_BOUNDED for statement correspondence | PKC V5 mismatch evidence |
| P3 | PKC | arbitrary nonempty text with no typed proposition interpretation | UNKNOWN | no semantic witness |
| Y1 | L4YAML | explicitly distinguished typed null and string "null" under independent reference reader | WARRANTED_BOUNDED only when actual instance preserves distinction | independent oracle |
| Y2 | L4YAML | `none` and `some "null"` same dumped value | REJECTED_BOUNDED for injective typed interchange | L4YAML RED |
| Y3 | L4YAML | unspecified YAML schema/reference semantics | UNKNOWN | no relation authority |

**Important:** P1 is not proof of optional statement correctness. Y1 is a *prospective positive challenge*, not a claim current L4YAML passes.

## Mutations and counterfactuals
M1 change PKC referenced declaration type; withdraw only decisions depending on that declaration.
M2 change PKC optional assertion; invalidate only its correspondence decision.
M3 change L4YAML scalar resolver or dump implementation; invalidate only evidence dependent on that exact source.
M4 withdraw one external YAML oracle; invalidate claims relying on that independent interpretation.
M5 restore original revisions and raw receipts; requalification requires verifier replay, not reverting a label.

## Success / failure boundaries
PASS only when a single frozen evaluator and distinct native witness adapters produce all six justified decisions, mutation M1–M5 dependency-selective withdrawal and requalification, and comparison with native baseline plus expert-authored equivalence rule. Audit source SHA, adapter SHA, protocol SHA, evaluator logs, raw native results, and resulting graph edges.

FAIL if any unsupported claim is admitted or any verified mismatch is promoted. UNKNOWN if a verifier, prerequisite, or native execution is unavailable. This document freezes a **test plan**, not an executed transferable protocol. No claim of cross-domain transfer may be promoted from this specification alone.

## External communication
Nicolas has already been sent the PKC case and question on optional-statement authority. Do not interpret silence as agreement; do not attribute endorsement to Nicolas, JPL, Caltech, or NASA. Do not send additional correspondence solely to report this protocol candidate.
