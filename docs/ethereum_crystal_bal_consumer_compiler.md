# Crystal on Ethereum EIP-7928: from consequential quotient to geth catch-up prototype

## Executive result

This campaign started from the hypothesis that the Minimal Sufficient Interface / Crystal programme might apply to Ethereum's EIP-7928 Block Access Lists. The strongest warranted result is now a **local, pinned go-ethereum snap/2 catch-up prototype**, not merely a finite model.

At `ethereum/go-ethereum@920c07774c65ebb3023536f85df642c44478b540`, Crystal's consequence analysis identifies that `snap.applyAccessList` observes only:

- account address;
- changed storage slot and its **final** post-value;
- final balance;
- final nonce;
- final code.

It does not observe storage reads, block-access indices, or intermediate changes during the apply phase.

A local prototype adds a compact `bal.DecodeApplyRLP` decoder and substitutes it for geth's second full BAL decode in snap catch-up. On the frozen 1,112-record held-out EELS corpus, it is consequence-equivalent to geth's production BAL objects. The native BAL package test suite and geth's pivot/catch-up regression tests remain green.

No upstream go-ethereum branch or pull request was created.

## Evidence ladder

### V8 — exact protocol reconstruction

Run [36354003831](https://github.com/metalogiclabs/mathgraph/actions/runs/36354003831) established exact reconstruction from the accumulated Crystal capability bank on 22 realized EELS BAL records across nine official families:

- 22/22 BAL objects reconstructed exactly;
- 22/22 `blockAccessListHash` values matched using EELS's own `BlockAccessList.rlp_hash`;
- every retained capability had a causal ablation witness on the realized corpus.

### V9 — broad unseen EELS corpus

Run [36354473773](https://github.com/metalogiclabs/mathgraph/actions/runs/36354473773) generated the full official Amsterdam EIP-7928 test directory and froze the original nine V8 families as seen.

Held-out boundary:

- **1,112 BAL records**
- **163 unseen fixture families**
- **488,357 raw BAL bytes**

Consequence-specific consumers preserved exact byte reassembly and fixture hash on every held-out record.

Python/EELS microbenchmark:

| consumer | median relative speed | peak allocation ratio |
| --- | ---: | ---: |
| dependency | **2.838x** faster | **0.0285x** |
| reconstruction | **1.517x** faster | **0.1410x** |

This was not treated as production evidence because the baseline used EELS/Pydantic.

### V10 — dependency-free optimized Rust replication

Run [36354980547](https://github.com/metalogiclabs/mathgraph/actions/runs/36354980547) reproduced the same frozen split with a common optimized Rust RLP scanner:

- dependency: **1.915x faster**, allocated-byte ratio **0.4264**;
- reconstruction: **1.186x faster**, allocated-byte ratio **0.8207**;
- exact reassembly on all 1,112 held-out BALs.

This rejected “Python/Pydantic overhead explains the whole effect”.

### V11 — inside go-ethereum's BAL package

Run [36355203318](https://github.com/metalogiclabs/mathgraph/actions/runs/36355203318) copied a benchmark-only dependency decoder into pinned geth's `core/types/bal`.

Before timing, the dependency fields were checked field-for-field against geth's production `BlockAccessList` decoder on all 1,112 held-out BALs.

Median result:

- full geth decode: **7,056,849 ns/op**
- Crystal dependency view: **2,710,536 ns/op**
- **2.603x faster**
- allocation bytes: **0.5288x**
- allocation calls: **0.6641x**

### V12 — compile to the actual snap apply consequence

Inspection of geth's real snap/2 consumer exposed a smaller protected consequence than V9 reconstruction. `applyAccessList` uses final state only.

Run [36355853836](https://github.com/metalogiclabs/mathgraph/actions/runs/36355853836) checked the compact apply view against production geth BAL objects on all 1,112 held-out BALs, then benchmarked it inside `core/types/bal`:

- full geth decode: **7,190,477 ns/op**
- apply view: **2,384,793 ns/op**
- **3.015x faster**
- allocation-byte ratio: **0.6856**
- allocation-call ratio: **0.09990** — about **90% fewer allocation calls**

### V13 — actual local snap/2 catch-up patch

Run [36355884299](https://github.com/metalogiclabs/mathgraph/actions/runs/36355884299) locally patched pinned geth so the second BAL decode in catch-up uses `bal.DecodeApplyRLP`.

Qualification:

1. compact decoder vs production BAL consequences on all 1,112 held-out EELS BALs — PASS;
2. `go test ./core/types/bal` — PASS;
3. patched snap path:
   - `TestPivotMovement`
   - `TestPivotMovementRepeated`
   - `TestCatchUpPersistsIncrementally`
   - `TestCatchUpWindowed`
   — PASS;
4. patch artifact persisted.

Median decoder benchmark on the authority run:

- full: **7,022,653 ns/op**
- compact: **3,128,757 ns/op**
- **2.245x faster**
- allocated-byte ratio: **0.79775**
- allocation-call ratio: **0.36177**

Artifact: [10944166947](https://github.com/metalogiclabs/mathgraph/actions/runs/36355884299/artifacts/10944166947), ZIP SHA-256 `cfb85d762120b8f6763afead18234d1b6c9673dbc09ccb65e91f2431f182d48d`.

## What Crystal actually contributed

The result is not “a hand-written fast RLP parser”. The developmental lineage was:

```text
insufficient interface
→ protected-consequence conflict
→ separator acquisition
→ causal ablation
→ held-out reuse without reacquisition
→ exact protocol-object reconstruction
→ broader unseen corpus
→ consumer-specific quotient
→ native replication
→ production-client consumer discovery
→ local client-path substitution
```

Several stronger stories were rejected on the way:

- BAL is not one globally compressible object; dependency and reconstruction consequences differ.
- An atomic `slot` feature was not a warranted first repair.
- `post` was not the unique residual coordinate in the finite abstraction.
- EELS generator tests could not be treated as ordinary pytest tests.
- Python/Pydantic overhead was not accepted as sufficient evidence for the speedup.

The durable law supported by this campaign is narrower and more useful:

> **A multi-purpose verified object can admit smaller consumer-specific interfaces. Once a distinction is verified as consequential for a consumer, compile and retain it; do not repeatedly materialize unrelated distinctions at that consumer boundary.**

## Current epistemic state

**WARRANTED / REUSABLE within the declared boundary**

- fixture-native Crystal acquisition from official EELS BAL objects;
- causal ablation and source-distinct held-out reuse;
- exact canonical BAL and hash reconstruction;
- broad held-out exactness over 1,112 BALs / 163 unseen families;
- optimized native replication;
- geth package replication;
- local geth snap/2 catch-up substitution with the declared regression tests green.

**UNKNOWN**

- whole snap/2 catch-up wall-clock improvement when network, database, hashing and trie work dominate;
- memory impact over production-sized catch-up windows in a running node;
- universal minimality for every possible EIP-7928 BAL;
- upstream geth maintainers' preferred API/implementation shape;
- cross-client benefit in Nethermind, Erigon, ethrex or other clients.

## Next decisive experiment

Do not change consensus encoding and do not enlarge the representation grammar.

The next useful experiment is an end-to-end geth snap/2 catch-up benchmark comparing the pinned baseline with the V13 patch on the same realistic multi-block BAL stream, measuring:

- catch-up wall-clock time;
- peak heap / allocation count;
- trie/database work;
- final state root equality.

If the end-to-end gain remains material, the research result is ready for maintainer discussion and an upstream-quality patch review. If it disappears under database/trie costs, retain V13 as a verified decoder optimization and do not overclaim client-level throughput.
