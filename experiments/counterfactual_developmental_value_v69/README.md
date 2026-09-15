# V69 — Counterfactual developmental value calibration

V67 showed that ranking individual generated lemmas does not transfer capability.
V68 showed that transferring the shared syntax of a causal generator action does
not transfer either.

V69 learns a different object: **the value of an intervention from the verified
descendant cone that the intervention causes**.

For each possible round-1 source/self critical-pair intervention, V69 performs a
tiny source-only rollout (two rounds, twelve retained descendants per round).
The exact V66 delete/restore causal roots are positives; alternative source/self
interventions are counterfactual negatives. A pairwise ranker is learned over
rollout features, not source IDs, equations, targets, labels, or verdicts.

Evaluation is intentionally the already-opened V67 Stage2 stream. It is
calibration only, not fresh evidence.

COLD and META receive exactly the same 16+15 derived-lemma budget. META changes
only round-1 allocation according to the frozen source-only counterfactual value
operator; round 2 returns to the identical cold complexity ordering.

A strong calibration signal requires a META-only proof, exact use of a
META-exclusive lemma, delete-lineage failure, restore success, and no loss in
overall coverage. If calibration is positive, the next version must freeze the
operator and move to a genuinely untouched external stream before making any
transfer claim.
