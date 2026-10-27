# Annals source-to-intent V1 — externally pinned negative witness

**Target.** Theorem 1.1 of Frankston–Kahn–Narayanan–Park,
*Thresholds versus fractional expectation-thresholds*, Annals of Mathematics
194(2), 2021, <https://annals.math.princeton.edu/2021/194-2/p02>.

**External formalization (read-only).** The Imperial College London
`AnnalsChallenge` file `AnnalsChallenge/AnnalsOfMathematics/2021-194-2-FractionalExpectationThresholds.lean`
at commit `e32eb1411db0d700ca874dd695aea92f78699db8`, byte SHA-256
`7c78b2b9b74582e5a1e683307029e6be1c3df938009969cb9704201cee3280f9`.
It **already documents** that the paper's displayed bound needs the additional
`l(F) ≥ 2` scope restriction. It is not our original discovery. Its formal
theorem is `sorry`, as is the universal constant `K`; neither is a verified
proof. No AnnalsChallenge or JPL upstream files are changed.

**One independently calculable countermodel.** Let `X = {x}` and
`F = {{x}}`. It is increasing. Its largest minimal member has size `l(F)=1`.
Bernoulli inclusion of `x` has probability `p`; thus `p_c(F)=1/2`.
The displayed **unguarded** bound has RHS `K × q_f(F) × log 1 = 0`, contrary
to `1/2 ≤ 0`, for any finite coefficient. The formalized theorem includes
`l(F)≥2`, so this is **not a counterexample to its formal statement**.

The Python checker enumerates the singleton sample space and rejects stale,
missing, mismatched or unrelated source content. Lean separately proves
the reduced Bernoulli probability and zero-factor obstruction for all rational
`K,q`, with a deliberately false Lean negative control rejected by the kernel.
The exact bridge from these reduced definitions to the original Mathlib
`p_c`, `q_f`, `l` and `Real.log` definitions is **not formally checked**.

**Evidence levels:**

- `FINITE_COUNTERMODEL`: only the reduced, unguarded singleton formula.
- `UNKNOWN`: the full original theorem, intended contextual hypotheses,
  formal equivalence of the reduced and Mathlib definitions, all larger
  families, and any general source-to-formal-language fidelity.
- `NAMED_OBSTRUCTION`: missing, changed or wrong source; fail-closed.
- **Baseline:** an equally informed ordinary finite probability calculation
  finds the same witness; observed advantage is **TIE**.
- **No authorization:** passing a formal proof, finite sample, or pinned source
  does not establish interpretation or justify automatic correction/publication.

Run in a checkout with sibling `AnnalsChallenge/` at the pinned commit:

```
python -m unittest discover -s tests -p 'test_annals_source_intent_v1.py' -v
```

CI additionally clones the published external source at the exact SHA and
retains the audit report, positive Lean log, and protected negative log.
