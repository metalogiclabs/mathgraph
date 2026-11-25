# EIK live competitive frontier — 25 November 2026

Status: WARRANTED bounded comparison; current candidates do not meet the recorded takeover bars. No registration, signing, payment or submission occurred.

The qualified joint source remains unchanged: `75faa8078e1c4982f1ce3430677114fc8991d292373aa266e2148d8a6351dc93`. Its [21-job exhaustive qualification](https://github.com/metalogiclabs/mathgraph/actions/runs/45566932685) remains valid within its pinned evaluator.

## Live authority and matched inputs

[Read-only official client run](https://github.com/metalogiclabs/mathgraph/actions/runs/45569614249), commit `c959c5714a08e90a38ae58cfd78b6f0125e0c9d8`, queried boards, all three leaderboards and reports 50/52. Six GET commands succeeded with client `5a32428ad4aa23bce737d50a738ace24ddeeed2e`. ARM promotion 57 and overall promotion 58 belong to entry 50; RISC-V promotion 59 belongs to entry 52. All boards are open; takeover multiplier 0.97.

[Independent matched-source run](https://github.com/metalogiclabs/mathgraph/actions/runs/45569905567), commit `a58e58b94461056dd1d1c76994d2017775245215`, passed. It reproduces the joint source on report 52's seed `1284956104`, requiring exact equality of input digest `0f0831296847c2100d1f2a25872b251a80e9920867420bb4b2bc4d3cd0c147ef` and live board environment measurement identity `2c8fd1f3a6711f0639685319fb25262b02bfecf4c6589c52cb58928270a46322`.

| Board | Current champion | Champion S | Joint S | Takeover threshold |
| --- | --- | ---: | ---: | ---: |
| ARM Cortex-M0+ | #50 | 40.3387547513 | 93.5524390505 | 39.1285921088 |
| RISC-V RV32IM | #52 | 28.1835146151 | 76.9471036301 | 27.3380091766 |
| Overall | #50 | 33.8739666378 | 84.8445002488 | 32.8577476387 |

These are matched historical evaluation inputs, not a new official submission or a prediction of every future seed. The discovery score 93.9470403227 and this replay score 93.5524390505 are different draws, not a contradiction.

## Reconciliation with the already running candidate comparison

[Three-source, two-seed run](https://github.com/metalogiclabs/mathgraph/actions/runs/45568993633), commit `df9c093210b4cc8a68ecf9e00d9ad4dd01e20a8c`, completed all three jobs successfully. Downloaded all three archives and independently matched their provider ZIP digests. Each source matches both measurement reports; latest-seed input hashes and live board measurement identities match.

| Retained source | Source SHA-256 | Closest board | S | Required reduction to takeover |
| --- | --- | --- | ---: | ---: |
| rrr | 3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4 | RISC-V | 29.1493208289 | 6.213906879% |
| ttt | ed3ed54da2dcd31861bfcc7f6533d16ab5020318cfe4f4e96ef9bcce2baf11d3 | ARM | 50.6991876865 | 22.822053184% |
| joint | 75faa8078e1c4982f1ce3430677114fc8991d292373aa266e2148d8a6351dc93 | ARM | 93.5524390505 | 58.174695918% |

The earlier comparison JSON's `measurement_match:false` represents a missing `compare.fingerprint` field, not evidence of unequal evaluators. The independent check uses the actual published board environment identity and passes. Preserve the earlier JSON as lineage.

## Registration quote

At 2026-11-25 07:37:51 UTC (20:37:51 NZDT), direct read-only Finney RPC at finalized block **9,582,348** returned Subnet 66 `Burn = 500000` rao = **0.0005 TAO** and `NetworkRegistrationAllowed = 0x01`.

Block hash: `0xd2077a7e616d8f240ef75f53a3c15ca8ddf28cc5e344936c54257eed36894a3d`.

Raw Burn SCALE: `0x20a1070000000000`; runtime version 495. Header, state root, read proof and RPC transcript are archived. This is a registration-price snapshot, excluding transaction fees; collateral split was not queried. No independent consensus or trie-proof verification is claimed.

## Evidence integrity and decision

- [Read-only query archive 15001462462](https://github.com/metalogiclabs/mathgraph/actions/runs/45569614249/artifacts/15001462462): SHA-256 `1998b23a9afbaa2a67c6dbea70eb308f417212eeef0a61bdbe9f71571200f724`; 24/24 manifest members independently rehashed.
- [Matched replay archive 15001089185](https://github.com/metalogiclabs/mathgraph/actions/runs/45569905567/artifacts/15001089185): SHA-256 `5f9165252c91d627bbc119ab78c32e02ea0c67e0e93cb778350d39066c003a6e`; 2/2 manifest members independently rehashed.
- Three-source archives: rrr `b642284d173d55b1809c4e4f9d77c4ba9fd437d8a8f5916a36fe0dedf32e0b8b`; ttt `946c35d9e62610547ca6cd34e09373b5fd65608f268d853544ebc222f1cc0583`; joint `0c6cb94ab6c158d769c15007f33c34ffe9c4d8f9f246d7aa44ebb52c2b2a8966`.

**Decision:** retain correctness evidence; do not spend a registration on these candidates. The nearest measured residual is the rrr RISC-V path: reduce 29.1493 to at most 27.3380 on these inputs, then verify improvement on fresh held-out seeds before exhaustive qualification or spending. A specific new transformation remains CANDIDATE until measured.
