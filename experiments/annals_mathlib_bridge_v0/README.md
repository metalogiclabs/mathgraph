# Exact-definition Annals singleton bridge V0 (candidate)

This is a distinct follow-on to [the green bounded Annals source-intent V1](https://github.com/metalogiclabs/mathgraph/actions/runs/40448158887).
It asks the cheapest narrower question: can we prove `l({{x}})=1` using
**the actual** `FractionalExpectationThresholds.l` definition at Imperial's
AnnalsChallenge commit `e32eb1411db0d700ca874dd695aea92f78699db8`
and frozen Mathlib revision `d1ddae43a4db43e0acf2d9d9e18b54037dbe3ea0`?

The source theorem and its `K` are admitted with `sorry`; successful import
of the file is **not** a proof of either. Even a positive `l=1` proof would
leave the exact `p_c({{x}})=1/2` bridge and paper intent **UNKNOWN**.

CI deliberately fails and retains diagnostics if this proof does not compile.
Do not promote this branch based only on a successful dependency checkout.
