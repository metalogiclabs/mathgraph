# Decision-sufficient observation: contract correction candidate (2026-10-21)

This is an exposed finite *specification gap* test on the already qualified [V1 compiler](https://github.com/metalogiclabs/mathgraph/commit/158681f999d1aa3336a09a7f66c52dc9cf7d925a), **not a prospective science result** and not a replacement of the original exact-quotient use case.

## Original mathematical contract
For a fixed declared finite snapshot, V1 computes an observation basis \`O\` with
\`kernel(O_old,O_new) = R_goal\`. In \`compiler.py\`, \`legal = [p for p in profiles if target <= kernels(p['values'])]\` rejects any individual experiment which refines a goal-equivalent pair. That is correct *when* exact observational quotient is the desired artifact.

## Missing downstream use case
For an experiment intended to establish a goal-relevant decision \`g:X→D\`, an observable program \`O:X→Y\` is *sufficient to decide* if there exists a decoder \`h:Y→D\` with \`g=h∘O\` on X.

For finite X, this is equivalent to \`kernel(O)⊆kernel(g)\`. The experiment may legitimately reveal additional, unprotected differences. Quotient **after** acquiring observations. For an experiment portfolio, measure joint observations. If an old observation interface exists, include its values in the joint tuple.

Three-state exact witness (unit-cost binary readouts, no effects, all readouts granted):
- \`g=[0,0,1]\`
- \`u=[0,1,0]\` and \`v=[0,1,1]\`.
- Each single readout splits the goal-equivalent states 0 and 1, so is excluded by V1 exact-quotient admission.
- Together the observation vectors are \`[(0,0),(1,1),(0,1)]\`. Decode \`(0,0)↦0\`, \`(1,1)↦0\`, \`(0,1)↦1\`: goal decision is completely determined, at minimum cost 2.
- Therefore V1's complete-grammar obstruction is valid ONLY for **exact observational quotient**, not for **decision sufficiency**. Any downstream claim that the desired decision is impossible to obtain would be unwarranted.

## Test method
Import the unchanged pinned V1 compiler; independently enumerate all 2-sensor subsets of the complete binary function space on 3 and 4 states and every set partition (5 and 15, respectively), recompute exact and sufficient decision optima from scratch without calling the V1 optimizer, check decoders and costs, compare with V1 native outputs. Include the original counterexample and a confidence boundary.

## Proposed minimal new mode (NOT implemented or promoted here)
\`mode=decision_sufficient\`: optimize least-cost experiments such that
\`ker(O_old,O_new)⊆R_goal\`, return a source-bound decoder and a verifier for its finite factorization. Keep \`mode=exact_quotient\` unchanged. Encode the policy/goal separately from observational syntax. Require explicit safe effectful transport (CLC) and authority grants; otherwise fail/UNKNOWN. Only after obtaining a source-authoritative goal and native observation semantics should real scientific transfer be attempted.

**Important limitations:** the finite functions and goal labels are human-supplied; no physical/new primitive was constructed; no human baseline or real biology is tested. The factorization lemma is elementary known mathematics. The independent optimizer is equal-information and should be given the same decoding option, so there is no claimed superiority. This is **a corrected problem statement, not a new algorithmic win**.
