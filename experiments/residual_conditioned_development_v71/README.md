# V71 — Closed-loop residual-conditioned development

V71 moves from open-loop ranking to a verifier-feedback loop.

After each small batch of exact source consequences is retained, a cheap proof-frontier probe identifies the best live residual. Candidate interventions are ranked by how much they can shrink that residual, exact one-step consequence novelty, and structural compression.

Three equal-budget developers are compared on the already-opened Stage2 calibration stream:

1. COLD — frozen 16+15 complexity development.
2. RESIDUAL — verifier-feedback loop with no learned prior.
3. META — the identical loop plus the learned V69 causal seed-value prior.

This separates generic target-guided search from benefit attributable to prior developmental experience. A decisive learned signal requires META to prove a target both baselines miss, use a META-exclusive verified lineage, and lose/restore the proof under exact lineage deletion/restoration.

Calibration only; no fresh stream is spent here.
