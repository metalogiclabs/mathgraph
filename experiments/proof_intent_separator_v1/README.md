# Proof-to-intent separator V1 — predeclared bounded experiment (2026-10-27)

## Question

Can a valid Lean proof coexist with a false or underspecified source intent, and
can a finite observer return a minimal separating witness/guard **without**
automatically authorizing a rewritten claim? This is a small controlled
integration test, not a natural-language understanding benchmark.

## Predeclared scope and controls

1. **Missing mathematical guard:** independently declared source intent says
   `∀ n : Nat, n ≥ 1 → n+n > n+1`. The submitted formal theorem requires
   `n ≥ 3`. Inspect `Nat[0..12]`, report the least counterexample, and find the
   weakest repair among *threshold guards* `n ≥ k` for `1 ≤ k ≤ 12`.
   Native Lean independently checks the guarded theorem, the suggested `n ≥ 2`
   repair on all natural numbers, and refutes the original source statement.
   A finite repair suggestion is never permission to edit the stated intent.
2. **Weak implementation specification:** a Lean-proved identity
   compression/decompression pair satisfies roundtrip but is not useful
   compression. Independently declare that homogeneous binary strings of
   length four must shrink. Exhaust all 31 binary words of length 0–4,
   requiring correct roundtrip, and separately test both four-symbol runs for
   strict size decrease. Compare with a tiny reversible three-symbol run
   encoding and a decoder mismatch negative. This is a toy codec model and
   does not validate zlib or any deployed compressor.
3. **Strong conventional baseline:** independently enumerate `n > 1` with the
   same universe and permitted threshold guards, with full source-intent
   access. Compare witness and minimum repair. A tie is recorded as a tie, not
   a MathGraph advantage.
4. **Fail-closed cases:** empty admitted source domain, vacuous proof domain,
   invalid negative Nat bound, false formal theorem, roundtrip-only promotion,
   lost decoder correspondence. Neither finite supported observation can issue
   action permission or a blanket global semantic-fidelity certificate.
5. **Source binding:** this deliberately starts with manually fixed formal
   intended claims. It **does not** infer the meaning of informal prose, verify
   an external paper's authorship, authenticate external statement identity,
   or establish general source-to-Lean correspondence.

## Verification boundary

Run `python -m unittest discover -s tests -p 'test_proof_intent_separator_v1.py' -v`.
The separate pinned native Lean job compiles `ProofIntentV1.lean` and demands a
nonzero exit for `RejectedFalseClaim.lean`, keeping logs, toolchain version and
source SHA256 in an Actions artifact. Any native failure or missing artifact is
`UNKNOWN` on the cross-tool result, not a proof refutation. No production gate,
default branch, third-party repository, or externally deployed service changes.

## Expected boundaries (before native CI)

- Finite counterexample `n=1`; proposed threshold `n ≥ 2`; the existing
  `n ≥ 3` proof remains logically intact.
- Identity codec: roundtrip PASS, compression-benefit failure on `0000`.
- Tiny codec: 31/31 roundtrips and 2/2 four-symbol size observations pass;
  mismatched decoder fails on `0000`.
- Independent finite baseline **TIE** on counterexample and threshold.
- General language fidelity, independent unseen domains, relative cost gains,
  and real authorization/revocation in an installed application: **UNKNOWN**.

## Relationship to prior evidence

This is not the first MathGraph source-fidelity test. Prior source-pinned
research already records 420 finite Bool-source pairs / 132 Lean samples in
[MathGraph Check machine-oracle V1](https://github.com/metalogiclabs/mathgraph/actions/runs/38011630309),
two Mathlib source-statement binding negatives in
[RealityGraph receiver-owned Lean replay](https://github.com/heathsanchez/realitygraph/actions/runs/38494606080),
and a real PKC `@Checked.statement` / cited-declaration discrepancy in
[the JPL-side bounded audit](https://github.com/metalogiclabs/mathgraph/blob/research/jpl-pkc-opensysml-e2e-v5-20261019/docs/research/JPL_CLAIM_ADVERSARY_60_SECOND_DEMO_20261019.md).
The modest additional focus here is *minimal repair*, an independent
mathematical proof of that repair, and a separate underspecified software
contract. Standard finite enumerators are expected to tie on this scale.
