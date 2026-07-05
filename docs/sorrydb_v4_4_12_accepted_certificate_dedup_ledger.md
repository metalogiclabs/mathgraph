# SorryDB v4.4.12 — Accepted Certificate Dedup Ledger

v4.4.11 produced four accepted hydrated backfill replay certificates after cache hydration.

v4.4.12 deduplicates those accepted certificates into semantic repair classes using source snippet, patch snippet, source file, repo identity, repo commit, and line span when available.

## Result

- accepted certificates: 4
- unique repair classes: 2
- duplicate certificate identities: 2

The two unique repair classes correspond to the two actual source repairs:

- eg₁ / line97 / `Nat.le_add_right`
- eg₂ / line99 / `Nat.succ_le_succ (Nat.le_add_right n 1)`

## Bounded claim

- v4.4.11 produced four accepted replay certificates.
- v4.4.12 deduplicates accepted certificates into semantic repair classes.
- the current evidence contains two unique repair classes and two duplicate certificate identities.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches
- general SorryDB mining
- arbitrary proof repair
- upstream submission
- that duplicate certificate identities are semantically distinct proofs
