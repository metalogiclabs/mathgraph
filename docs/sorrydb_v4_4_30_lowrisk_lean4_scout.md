# SorryDB v4.4.30 — Low-Risk Lean4 Scout

v4.4.30 parks the medium-high-risk Lean3/equate candidate and scouts lower-risk Lean4/Nat/simp candidates.

## Bounded claim

- v4.4.30 parks the medium-high-risk Lean3/equate attempt002 candidate.
- it scouts lower-risk Lean4/Nat/simp candidates using GitHub API inspection only.
- it selects one candidate for future bounded clone/recon without running Lean.

## Does not claim

- new proof discovery
- new Lean replay
- candidate repairability
- that the selected repo builds locally
- that the selected source still matches after clone
- upstream acceptance
- automated external contact

## Next frontier

v4.4.31 clone only the selected low-risk Lean4 candidate into a bounded temp directory and run manifest/source reconnaissance before replay.
