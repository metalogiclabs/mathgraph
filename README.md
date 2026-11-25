# Independent PKC assurance — bounded evidence record

Pinned source: 97153d3fad3cb8e5e018d2df5f7aeb4a406ff7e4. See assurance.json for all 28 requirement rows and evidence lineage. This is an inventory, NOT a universal audit certificate.

## Three witnesses

A: 8/132 original numeric discrepancies, 0/132 repaired, using existing TorchLean reachability-preserving API. [Native run](https://github.com/metalogiclabs/mathgraph/actions/runs/45532422248).

B: catalogue metadata marks an unrelated theorem and data declaration as proved. [Native run](https://github.com/metalogiclabs/mathgraph/actions/runs/45533439112). This is not a test of R28's separate model-boundary gate.

C: clean adequacy report despite an invisible operand perturbation; even/odd midpoint controls. [Native run](https://github.com/metalogiclabs/mathgraph/actions/runs/45532760201). Clean-report completeness is expressly not certified upstream.

## Next gates

1. Full gradient regression, signed-zero observation, active singular controls.
2. Define explicit per-operand perturbation contracts (input-rounded vs exact perturbation of rounded sum), then prove checker soundness for that contract.
3. Test typed entailment certificates separately from catalogue metadata; inspect actual R28 model-boundary checks before making claims.
4. Blind transfer experiment versus baseline investigation; no novelty or funding assertion yet.

No upstream changes. Artifact digests recorded from GitHub metadata, not independent byte checks. All requirements remain UNKNOWN at full semantic-audit level.
