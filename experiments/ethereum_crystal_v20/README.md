# Ethereum Crystal V20 — CPU-time replication of authenticated catch-up

V19 established exact protected-effect parity through geth's real authenticated `syncerV2.catchUp` + Pebble path, but its wall-clock A/B was noisy: the arm medians favored Crystal by about 2.7%, while several paired trials were dominated by hosted-runner scheduling outliers.

V20 changes **measurement only**. The semantic implementation, geth/EELS pins, frozen 1,112-record corpus, synthetic linked header fixture, peer authenticity path, windowing, pivot persistence, and Pebble writes are unchanged.

## New measurement

Each stock/Crystal trial records:

- catch-up wall time;
- durability-inclusive wall time;
- process user+system CPU time for catch-up;
- durability-inclusive process CPU time.

CPU time is read with Linux `getrusage(RUSAGE_SELF)`, so host descheduling does not count as work performed by the geth test process.

The workflow runs **21 fresh-process alternating pairs**.

## Prospective interpretation rule

Correctness is a hard gate: all 42 arms must have one identical final DB digest, one identical final pivot, and matching nonzero authenticated BAL-request counts.

The primary performance statistic is the **paired stock/Crystal catch-up CPU-time ratio**.

- **WARRANTED_PERFORMANCE** only if the paired median ratio is >1, at least 14/21 pairs favor Crystal, and a deterministic paired bootstrap 95% interval for the median ratio is entirely >1.
- **NARROWS** if the paired median ratio is >1 but that promotion gate is not met.
- **REJECTS_DIRECTION** if the paired median CPU ratio is <=1.

No wall-clock threshold is used for promotion. Wall and durability metrics are retained as secondary evidence.

The declared boundary remains V19's: phaseDownload/no-trie catch-up over a synthetic linked chain carrying the 1,112 independent official BAL fixtures, with no socket transport and no canonical-mainnet claim.
