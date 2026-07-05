# SorryDB v4.4.29 — Attempt 002 Repo Recon

v4.4.29 clones the selected attempt002 repo into a bounded temporary directory for reconnaissance before replay.

## Bounded claim

- v4.4.29 clones the selected attempt002 repo into a bounded temporary directory for reconnaissance.
- it records manifest files, target-file presence, sorry count, and Lean-version risk before replay.
- it does not run Lean, build the repo, modify upstream, or contact maintainers.

## Does not claim

- new proof discovery
- new Lean replay
- candidate repairability
- that the repo builds locally
- that the selected sorry has a repair
- upstream acceptance
- automated external contact

## Next frontier

v4.4.30 either install/locate a safe Lean3 replay path for this candidate or park it and choose a lower-risk Lean4/Nat/simp target.
