# Audit repair status

V2.1 replaces the two controls identified as weak in the first external audit:

- A-only shams are now instantiated as explicit regimes with observation maps `(A, q(A))`; their induced partitions are compared against M0, and the synthesizer is rerun under all four sham regimes for every target and every strict-growth pair.
- The former “ancestor ablation” wording is replaced with explicit reconstruction of the frozen parent regime followed by the unchanged synthesis procedure. This is reported as a finite counterfactual parent-regime replay, not as an empirical intervention.

The exhaustive target universe, exact minimal-extension classification, x/y equivariance, and independent closed-form count checks are unchanged.
