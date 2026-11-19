# MathGraph Check rocket native replay v1

**CANDIDATE / research-only; stacked on [draft PR #281](https://github.com/metalogiclabs/mathgraph/pull/281).** No production Check, Cloudflare, GitHub App permission, external maintainer, or operational requirement changes.

## What is independently run

The exact public upstream revisions are fetched using pinned GitHub Actions checkouts:
- NASA-SW-VnV/fret: cf0f913cc15c41705e803593297e89cd6056b839.
- R2U2/r2u2: 2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a.

`export_rocket_native.mjs` invokes **actual** FRETish `FretSemantics.compile` on the published example ("whenever BOOST, the sounding_rocket shall within 7 seconds satisfy COAST"), requires its exact [0,7] R2U2 stream output, and uses the original FRET renderers to produce C2PO source, map and four Boolean CSV traces. The [1,7] variant is **constructed by MathGraph** for comparison, not another FRET result and not an authorized repair.

`native_replay.py` checks source and signal-map content digests against frozen known references, invokes C2PO to produce two genuine compiled binaries, executes the source-pinned native R2U2 C monitor, expands its documented aggregated interval verdicts, and checks 64 output positions against a finite oracle. It refuses altered map/header and swapped compiled binary; the source and generated artifacts remain attributable to this bounded job. It emits an **unsigned native evidence manifest**, never an owner-permission warrant.

`qualify_native.py` executes separately in another GitHub job. It downloads the first job's actual bytes, rebuilds the pinned native C monitor, rehashes source/map/binary artifacts, verifies its own exact monitor binary identity, independently computes the expected truth values and checks 64 positions against the downloaded binaries. Mismatched binaries/versions fail closed; no claimed green status or in-band approval is trusted.

## Contract checks

11 local unit tests cover source and trace semantic controls, aggregation, incomplete/malformed verdict refusal, binary/map/header substitution, forged owner fields, changed reported digests, and false census. CI runs those tests before native generation. The original source-only rocket PR #280 and common-mode PR #281 remain independent historical evidence, not silently promoted.

## Warrant and authorization boundary

A successful run warrants **only** the executed 4 complete eight-tick Boolean scenarios, two formula variants and the declared source/binary identities. It cannot establish whole-MLTL correctness, that the [1,7] change reflects actual mission requirements, that an R2U2 defect exists, or that any operating mission should deploy a patch.

Top-level purpose/mission claim: **UNKNOWN**. Operational owner decision: **UNKNOWN**. Automatic repair: **DENIED**. Permission: **ADVISORY_ONLY**.

An unsigned receipt generated inside a CI job is a reproducible record **only within that run's declared trust boundary**. It is not an independently authenticated human acceptance of mission meaning; source digests alone do not supply requirement authority.

## Run / evidence lineage

Run unit contracts:

```sh
python3 -m unittest discover -s experiments/check-rocket-native-v1 -p 'test_*.py' -v
```

Actual replay requires pinned public FRET/R2U2 checkouts, Node 24, Python 3.13, GNU make/GCC, and isolated npm modules `antlr4@4.8.0` plus `product-iterable@3.0.1`. Follow [.github/workflows/check-rocket-native-v1.yml](../../.github/workflows/check-rocket-native-v1.yml) for exact commands.

GitHub workflow's first job performs source/allowed-diff checks, genuine native replay and evidence upload. Second job checks the downloaded artifacts. Failures remain failures or UNKNOWN: no fake evidence, skipped job or screenshot is treated as approval. The private source-only ZIP sent to Kristin is *not* uploaded to this PR.

## High-leverage next step

After a successful exact-head two-job run: independently bind a legitimate requirement owner's decision about simultaneous BOOST/COAST (or preserve UNKNOWN), then test source/approval and binary replacement selectively withdrawing affected warrants. Prospective discovery advantage against an equally informed reviewer remains UNKNOWN.
