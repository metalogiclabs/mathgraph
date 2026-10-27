# Annals exact probability and unguarded counterexample bridge

Test the one-point Bernoulli event against the **authentic**
AnnalsChallenge/Mathlib definitions of `setBer`, `p_c`, `q_f`, and `l`.
The staged native proof obligations are:

1. `setBer(univ,p).real {{x}} = p`, using Mathlib's `setBernoulli_real_singleton`.
2. `p_c({{x}}) = 1/2`, using an explicit witness and the source's
   `Classical.choose` conditional.
3. `l({{x}})=1`, using the source's proof-indexed supremum.
4. For every real `K`, the unguarded displayed inequality fails when
   `F={{x}}` because its right-hand side contains `log 1 = 0`.

The real **guarded** theorem in the source assumes `2 ≤ l F`, so this case
does not refute that theorem. Nor is it a new discovery: the AnnalsChallenge
source comment already identifies the missing hypothesis. We do not claim
to have checked the paper's proof, its authors' intended scope, or `K`.

Pinned external authority: ImperialCollegeLondon/AnnalsChallenge commit
`e32eb1411db0d700ca874dd695aea92f78699db8`, Lean 4.33.0-rc1, Mathlib
`d1ddae43a4db43e0acf2d9d9e18b54037dbe3ea0`.

Lineage: [source-native `l=1`, `log l=0` green](https://github.com/metalogiclabs/mathgraph/actions/runs/40451809112),
[earlier reduced countermodel green](https://github.com/metalogiclabs/mathgraph/actions/runs/40448158887).

The initial [RED event run](https://github.com/metalogiclabs/mathgraph/actions/runs/40452403338)
confirmed Lean does not treat the nontrivial probability identity as
definitional equality. The [GREEN event run](https://github.com/metalogiclabs/mathgraph/actions/runs/40452646366)
proves it using pinned Mathlib. The [RED choice run](https://github.com/metalogiclabs/mathgraph/actions/runs/40452952793)
and [RED rewrite run](https://github.com/metalogiclabs/mathgraph/actions/runs/40453213417)
were repaired by a direct `split_ifs`; the [GREEN exact `p_c` run](https://github.com/metalogiclabs/mathgraph/actions/runs/40453689812)
reports only `[propext, Classical.choice, Quot.sound]` for both the event law
and the critical-probability result, no `sorryAx`.

The [RED combined counterexample run](https://github.com/metalogiclabs/mathgraph/actions/runs/40453988660)
contains a deliberately unfinished target (`rfl` failed). Later runs must
separately establish the combined theorem before it is promoted. Imported
upstream `K` and its main theorem still contain `sorry` and remain excluded
from our warrant.
