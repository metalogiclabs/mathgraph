# Real native semantic mutation → warrant withdrawal → native restoration: qualified chain

Status: **WARRANTED_BOUNDED** for one source-authority dependency and one isolated YAML semantic mutation. General autonomous cross-domain discovery **UNKNOWN**.

## Three independently archived, passing GitHub Actions runs

1. Historical PKC × L4YAML authenticated replay: https://github.com/metalogiclabs/mathgraph/actions/runs/39192207386 ; artifact 12160585927; SHA256 `872001d926a39b65447db55dce4a7328c28ac7a762f73d71198a0c327b765ae2`.
2. Fresh L4YAML source mutation, native Lean rebuild, independently decoded YAML, exact source restoration and native re-execution: https://github.com/metalogiclabs/mathgraph/actions/runs/39192635360 ; artifact 12160483329; SHA256 `6b842e6e247251fa36a530bb8af3372d133415652cd1e7622ef580d00ef7002d`.
3. Independent SHA256 authentication of both prior artifacts and receipt-driven warrant requalification: https://github.com/metalogiclabs/mathgraph/actions/runs/39193015909 ; artifact 12161110618; SHA256 `2656c8267d8b2e22c9523680bd368d727f1fc32d7f4472d602d68d24a680c1f2`.

## Exact observed transition

- **Before:** P1 WARRANTED_BOUNDED (PKC citation validity); P2 REJECTED_BOUNDED (false attribution); P3 UNKNOWN; Y1 UNKNOWN; Y2 REJECTED_BOUNDED (L4YAML original typed-interchange collision); Y3 UNKNOWN.
- **Native intervention:** an isolated temporary change of `L4YAML/Output/Dump.lean` default `allowReservedPlain` from false to true. Recompiled and reran Lean probe. Independent YAML 1.2 oracle changed type interpretations of `none`, `qNone`, `qStringNull`, `true`. Crucially, `qNone` and `qStringNull` remain collapsed.
- **Authority withdrawal:** the historical Y2 claim is invalidated for the **mutated revision**, so Y2 → UNKNOWN_WITHDRAWN. No PKC verdict changes, no invented Y1 positive warrant, no Y3 promotion.
- **Actual restoration and native replay:** restoring exact pinned source, rebuilding and rerunning yielded the exact original 11 native check results, emitted YAML texts, and independent-reader semantics. The original revision's bounded Y2 warrant can be restored; it is not a statement about the mutated revision.

## Epistemic limits

The withdrawal mapping is **expert-authored**: the evaluator already knows that Y2 depends on the YAML dump/source authority. Native receipts determine when that declared dependency was invalidated and when replay restores it. This is consequential, evidence-driven qualification for one authority edge, **not** autonomous invention of a new dependency graph and not general equivalence checking. The intervention is an experimental policy change, not a repaired L4YAML implementation, and upstream is unmodified.

Frozen protocol `9c8b427c679398fd80ea56d9a91a1627b2e96b6d` was not changed. PR #170 remains research-stage; do not imply JPL endorsement.
