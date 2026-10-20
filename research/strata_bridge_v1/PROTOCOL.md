# Strata VC/SMT bridge — exposed cross-source transfer V1

## Status and admissibility
EXPOSED retrospective transfer, **NOT prospective discovery**. The semantic defect in
[Strata #1488](https://github.com/strata-org/Strata/issues/1488) and the proposed correction
[PR #1490](https://github.com/strata-org/Strata/pull/1490) were already publicly
read before this protocol. No generalization to untouched source or independent
method invention may be inferred.

## Exact original source identities
- Strata main: `0bbe12d22650dc12dc4adc15249c965ba5ade8e3`
- Proposed upstream PR fix: `4016549f846065b5cab405fc09cff9a35d13512f`
- Toolchain: each source revision's committed `lean-toolchain` and `lake-manifest.json`.
- Tests: the two unchanged probes in this directory, copied to each clean revision
  only for compilation. No modifications to upstream content, proof scripts, or
  checks between the two revisions.
- Existing resolver: `mathgraph_check/warrant_resolution.py` from this
  MathGraph repository (unchanged).

## Before observing fresh compilation results
1. A complete source library build must succeed on each exact revision.
2. The same control Lean file must compile in both and establish both
   native BitVec / 0 = 0 and SMT-LIB smtUDiv 0 0 = 255.
3. The same exposed bad VC must compile on main **with a visible
   `_genSMTVCs_tcbBridge` dependency and no `sorryAx`**, and must **fail**
   on the proposed repair, with a semantic mismatch in the reported goal.
4. Passing kernel elaboration of `False` in main does not refute Lean
   kernel soundness: the bridge adds an explicitly trusted axiom. Do not
   call the generated theorem an axiom-free proof.
5. Both directions of withdrawal/restore through existing MathGraph
   least-fixed-point resolver must remove exactly the dependent
   documentary observations, preserving unrelated control and a
   surviving alternative support route.
6. The source-to-goal semantic-fidelity claim is **never admitted** by the
   presence of a compiled Lean theorem alone. The repair may qualify a
   **specific** counterexample refusal but not all-operator soundness.
7. Record full source identities, native output, raw diagnostics, proof
   axiom lists, artifact hashes, and all failed apparatus attempts.

## Threats to inference
- The fix PR may be updated or merged independently; test these exact SHAs.
- Rust/Lean (Aeneas) and SMT/Lean (Strata) semantic equality are different
  applications of a shared *warrant closure policy*, not a proof of an
  automatic observer grammar, universal translation correctness, or
  prospective cross-project transfer.
- The reported Lean `False` theorem has nonstandard bridge and
  native-decision trust dependencies; do not infer intrinsic logical
  inconsistency of Lean 4.
- Build failures, missing binaries, resource exhaustion, or parsing errors
  do not count as the repair correctly rejecting the bad VC. STOP UNKNOWN.
- No upstream issue/PR write or deployment is authorized by this experiment.
