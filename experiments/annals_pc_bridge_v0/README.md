# Annals exact probability bridge — candidate

Test whether a one-point Bernoulli event has probability `p` according to the
**authentic** AnnalsChallenge/Mathlib `setBer` definition. Only that event law
is tested first; do not silently assert `p_c({{x}})=1/2` or the paper theorem.

Pinned external authority: ImperialCollegeLondon/AnnalsChallenge commit
`e32eb1411db0d700ca874dd695aea92f78699db8`, Lean 4.33.0-rc1, Mathlib
`d1ddae43a4db43e0acf2d9d9e18b54037dbe3ea0`.

Lineage: [source-native `l=1`, `log l=0` green](https://github.com/metalogiclabs/mathgraph/actions/runs/40451809112),
[earlier reduced countermodel green](https://github.com/metalogiclabs/mathgraph/actions/runs/40448158887).

The initial [RED run](https://github.com/metalogiclabs/mathgraph/actions/runs/40452403338)
confirmed Lean does not treat the nontrivial probability identity as
definitional equality. The repaired candidate uses pinned Mathlib's
`setBernoulli_real_singleton` theorem. Inspect its native axiom report;
imported upstream
`K` and main theorem contain `sorry` and are excluded from warrant.
