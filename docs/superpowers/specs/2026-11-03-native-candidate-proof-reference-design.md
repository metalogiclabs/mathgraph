# Native actual-candidate proof reference — operator-only design

## Purpose and boundary

The existing generic consumer check compiles the actual Candidate source and a separately operator-authorized Consumer source, but does not tell whether the Consumer theorem's proof term even mentions the candidate theorem. The hypothetical SemantEq proof fixture checks stronger relevance on a **different** proof, and must not be promoted as actual candidate use.

Add a distinct, narrowly named native observation: after compiling exact bytes, the **zeta-reduced proof term** of the specified Consumer theorem has a direct occurrence of the specified Candidate theorem constant, both declared in the staged modules. The result is never called semantic necessity. Zeta reduction removes syntactically unused `have`/`let` bindings; a remaining reference can still be logically redundant, and indirect helper dependencies may be missed. This is a reusable audit boundary, not research-intent approval.

## Alternatives

- Selected: a generated Lean `run_cmd` audit of the actual elaborated proof value, using module-origin checks and `Meta.zetaReduce` before constant traversal. Runs in the same pinned native consumer replay and retains exact command/source/environment receipts.
- Future: native proof-dependency graph with transitive helper expansion and an antecedent-free replay/ablation for semantic relevance. Do not infer that result from a mere occurrence.
- Rejected: source-text search or raw proof-term occurrence; both can promote dead references.

## Contract

Optional `candidateName` to the operator-only `runGenericLeanConsumer` requests the audit. The candidate and consumer theorem names are whitelist-validated. The audit must require theorem origin in `Candidate.olean` and `Consumer.olean`, reject imported/library impersonation, check both axiom sets (no `sorryAx` or custom axiom for promotion), parse one unique native marker, and retain the raw Lean commands and output. Missing native environment, compilation error, wrong name, untrusted source bytes, ambiguous marker, false normalized occurrence, or nonstandard axioms yields `actual_candidate_proof_term_reference: UNKNOWN` with the underlying reason.

Even a positive reports only `NATIVE_ZETA_NORMALIZED_DIRECT_REFERENCE`. `candidate_dependence`, `intent_fidelity`, and `evidence_warrant` remain `UNKNOWN`. No GitHub App runtime change, arbitrary-PR execution, or public math warrant.

## Controls

Native positives: exact candidate proof imported and used by the actual Consumer theorem. Negatives: a library proof, an unused candidate theorem `have`, wrong theorem name/origin, sorry candidate, stale source hash, missing native environment, and duplicate/forged markers. Entire existing suite must still pass.
