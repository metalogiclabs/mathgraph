# SorryDB v4.4.31 — Commented Sorry Filter

v4.4.31 filters cached low-risk candidates for active, non-comment `sorry` lines.

## Bounded claim

- v4.4.31 detects that the v4.4.30 selected sorry is commented out and parks it.
- it re-ranks cached low-risk candidates by active non-comment sorry lines only.
- it selects the next active-sorry candidate without cloning, building, replaying, or contacting upstream.

## Does not claim

- new proof discovery
- new Lean replay
- candidate repairability
- that the selected repo builds locally
- that selected source still matches after clone
- upstream acceptance
- automated external contact

## Next frontier

v4.4.32 clone only the selected active-sorry candidate into a bounded temp directory and run manifest/source reconnaissance before replay.
