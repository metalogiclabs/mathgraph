# Ethereum Crystal V22 — prospective CPU replication at completed-state catch-up

V21 closed the semantic composition: frozen Crystal crossed geth's real authenticated `syncerV2.catchUp` in `phaseComplete`, with full account/storage trie maintenance, Pebble writes, persisted pivot advancement, and geth checking every block's computed post-state root against its header.

V21's three paired trials all favored Crystal, with an observational paired apply-CPU median ratio of about 1.02756. V22 does not change the implementation or fixture. It only applies the already-used V20 prospective replication rule at this stronger completed-state boundary.

## Frozen experiment

- geth: `920c07774c65ebb3023536f85df642c44478b540`
- EELS: `84e7d2c266e3319fc3882e72f379282bb1c40f2d`
- corpus: unchanged 1,112 held-out Amsterdam EIP-7928 BAL records
- stock and Crystal source trees: exactly the V21 construction
- sequential root-chain builder: unchanged and outside the measured catch-up region
- measured path: unchanged V21 `phaseComplete` authenticated catch-up + trie maintenance + per-block root verification + Pebble

The run uses **21 fresh-process alternating stock/Crystal pairs**.

## Frozen interpretation rule

Primary metric: paired stock/Crystal `ApplyCPUNS` ratio.

- **WARRANTED_PERFORMANCE** iff:
  - paired median ratio > 1,
  - at least 14/21 pairs favor Crystal,
  - deterministic paired-bootstrap 95% lower bound > 1.
- **NARROWS** if the paired median is >1 but the full promotion gate is not met.
- **REJECTS_DIRECTION** if the paired median is <=1.

Correctness is a hard gate across all 42 arms: one final DB digest, one final pivot, one final state root, one root-chain digest, and matching nonzero authenticated BAL-request counts.

No decoder retuning, threshold selection, corpus change, or post-hoc performance criterion is allowed.

## Boundary

A positive V22 warrants a CPU reduction on the deterministic completed-state geth catch-up boundary. It still does not establish socket/network benefit or live-mainnet wall-clock speedup.
