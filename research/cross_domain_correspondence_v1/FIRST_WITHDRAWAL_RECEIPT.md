# Cross-domain V1 first selective-withdrawal execution — 2026-10-19

**Status: CANDIDATE; model-level dependency selectivity tested, native cross-domain transfer UNKNOWN.**

Frozen protocol: [9c8b427c](https://github.com/metalogiclabs/mathgraph/commit/9c8b427c679398fd80ea56d9a91a1627b2e96b6d). This work does not edit that protocol.

The repository now has `receipt_model.js` and a CI workflow. The test takes previously documented PKC V5 and L4YAML RED outcomes as **manually encoded receipt assertions**, rather than ingesting/verifying the raw artifact bytes. Its bounded historical authorities are:
- PKC https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785
- L4YAML https://github.com/metalogiclabs/mathgraph/actions/runs/39183206058

A separately executed decision-logic check in the research session produced:

| Case | Initial modeled status | Meaning |
|---|---|---|
| P1 | WARRANTED_BOUNDED | declaration check only |
| P2 | REJECTED_BOUNDED | false attribution |
| P3 | UNKNOWN | free text lacks semantics |
| Y1 | UNKNOWN | repaired positive witness not available |
| Y2 | REJECTED_BOUNDED | typed collision |
| Y3 | UNKNOWN | schema authority absent |

| Mutation | Model verdicts changing | All other model verdicts unchanged? |
|---|---|---|
| M1 withdraw PKC declaration | P1, P2 | yes |
| M2 withdraw PKC annotation | P2, P3 | yes |
| M3 withdraw YAML dump | Y2 | yes |
| M4 withdraw YAML independent oracle | Y1, Y2 | yes |

Note: an already UNKNOWN verdict becoming UNKNOWN_WITHDRAWN is *not a lost warrant*. Thus M2 loses one negative decision and annotates an already unknown P3; M4 loses Y2 and annotates already unknown Y1. Restoring the in-memory dependencies restored the modeled baseline, **not** an earned M5 verifier replay.

Outstanding before protocol success may be claimed:
1. Download/verify raw PKC and L4YAML native artifact checksums and parse independently authenticated machine-readable receipts rather than manually asserting historical results.
2. Bind claim fingerprints and evidence hashes to the native verifiers and original pinned commits.
3. Implement native source mutation/requalification with actual reruns, and compare to the equally informed expert-written baseline.
4. Confirm CI outcome and archive its output. Creating workflow source is not confirmation that Actions executed.

**Verdict:** bounded shared verdict rules and modeled selective dependency withdrawal have been exercised; cross-domain native protocol reuse is **UNKNOWN**, and no positive L4YAML repaired semantics have been admitted.
