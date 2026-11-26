# Numerical continuation — 26 November 2026

**No winning entry.** The continuation measures 276 distinct candidates and
one duplicate pilot. Of those sources, 275 pass the declared scored-output
checks and one fails. No source reaches the predeclared 0.5% training gain.
The best apparent improvement is 0.013922%, so the frozen held-out draw is
not consumed and no candidate is promoted.

## Pinned comparison

Published baseline #49 has SHA-256
`8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37`.
Its attribution and licensing are retained. The official evaluator is
`conjectures-io/exact-integer-kernels-miner` at
`5a32428ad4aa23bce737d50a738ace24ddeeed2e`.

All measurements below use RV32IM, seed 1284956104, with extra target sampling
disabled. Every scored output is still checked by the kit. All 278 report
files, including the control and duplicate pilot, have matching input digest
`0f0831296847c2100d1f2a25872b251a80e9920867420bb4b2bc4d3cd0c147ef`,
measurement identity
`d3c13044e510324fe01259f6804ebd749f4217c5e3fb57cb5fb91d8d4e1213c2`,
and verifier identity
`28aad95db9f25d33eabaf31a8c6fc0b8d5070aa087f962da4972d5ca16a718fc`.
These local identities differ from the hosted contest identities. The local
performance comparisons do not claim a hosted takeover.

| Experiment | Distinct measured changes | Best RV32IM S, lower is better |
|---|---:|---:|
| Unmodified published control | 0 | 29.0515378858 |
| Grouped branch hints | 15 | 29.0474932837 |
| Single-condition hints | 248 | 29.0481783903 |
| Direct negative-sigmoid cubics | 4 | 29.4006309331 |
| Sigmoid tier changes | 2 | 29.0899859982 |
| Packed negative-exp variants, including one failing prototype | 7 | 30.3354911219 among corrected variants |

The hint sweeps preserve the original condition and arithmetic. All 248
single-condition reports passed; no apparatus-error files remain. All 266
control/hint/tier source files were independently reconstructed and hash
checked against the measured files. Reconstructing the final uniform analytic
generator also reproduces all four generated source hashes exactly.

The negative-sigmoid synthesis enumerates every input word in 104 complete
cells, `[0xbe600000, 0xc0000000)`, 27,262,976 words. A fixed low-byte guard
returns the fitted result only where its integer quotient matches the pinned
source; other inputs use the old evaluator. These source-relative guarded
cell checks do not establish full correctness of the integrated candidate.
The four integrated development measurements pass, but all are slower.

## A concrete failed composition, and its repair

The packed negative-exponential proposal co-designs a cubic coefficient,
constant and low-byte guard. For the exact source-oracle output word Y and
evaluated polynomial term p, exhaustive cell replay bounds

```
L = max(-256 Y - p)
U = min(255 - 256 Y - p)
D = L + ((cubic - L) mod 256)
threshold = max(0, D - U - 1)
packed = (threshold << 24) | (cubic mod 2^24)
base = (packed - D) / 256
q = packed + p
```

Subject to the checked coefficient and nonwrapping integer ranges, a return
is permitted only when `(q << 24) > packed`, using 32-bit unsigned arithmetic.
Every such return is replayed against the exact source-oracle Y over every
word of its cell. Fit estimates alone admit nothing. Five arithmetic tests
exercise the packing contract, signed-halfword repacking, range rejection,
and deliberate counterexamples to excessive guards and correction reuse.

The first integrated prototype reused the old residual correction on declined
inputs, with `base - (q >> 8) + 1` as its upper candidate. That composition
fails even though every admitted fast return matches the source oracle. The
old correction also requires its original approximation's rounding phase.
The new guard's error interval does not establish that precondition.

The rejected prototype has SHA-256
`5c301ea63a4770bcae416180b6ecd3f86c241788b27b757834911dc59d662174`.
Full native comparison of its changed interval,
`[0xbe680000, 0xc1000000)`, finds **501,990 mismatches among 43,515,904 words**.
Its first failure is:

| Input word | Published control | Reused correction |
|---|---|---|
| `be92003a` | `3f407c39` | `3f407c38` |

Replacing only the uncertain fallback with the complete range reducer yields
**zero mismatches over all 43,515,904 words**. Nine concrete failures, including
the first eight native failures and a scored-input failure, also reproduce on
RV32IM and return the control result after repair. The corrected source still
scores 30.4085628683, so it is rejected for performance.

A separate analytic proposal uses either one uniform grid or three complete
groups with finer cells at larger magnitudes. Mixed-grid cap16 scores
31.7099083685. The best measured corrected uniform variant scores
30.3354911219. The latter also matches the control on the complete 43,515,904
changed words. Both corrected sources pass a further 9,582,336 broad native
comparisons each. These are finite, source-relative comparisons, not independent
correct-rounding verification over all inputs or all targets.

The smaller `fallback_phase_replay.py` projection preserves one complete
131,072-word cell from the failed experiment. Its old correction produces
9,222 disagreements; its full-evaluator fallback produces zero. A fixed
RV32IM case corroborates both results. This projection is a regression fixture
selected after the failure, and its instruction counts are not contender
scores. Independent hosted [run 45745450707](https://github.com/metalogiclabs/mathgraph/actions/runs/45745450707)
passed at source `41c240240af9a722a391283956776395fc56d261`, tree
`b92c5aade7f66a19d4021ad9c557ebcf97a923ba`. Its actual job logs confirm all
five arithmetic tests, 9,222 legacy disagreements versus zero repaired
disagreements in that complete cell, and the fixed RV32IM case. Its measurement
identity is `2c8fd1f3a6711f0639685319fb25262b02bfecf4c6589c52cb58928270a46322`
and verifier identity is
`ebbf9d5cac596a718532b34798dc452e4050d6940594005c44f9a729c699c5a8`, matching
the published contest environment. This hosted result confirms the scoped
regression, not the 276 development performance measurements or whole-domain
correctness. Provider artifact `15082399085` was independently downloaded;
its SHA-256, ZIP CRC and all 11 member hashes were checked. Archive SHA-256:
`c741430631882c284f12b07a6c7f4544b0e376e750c30ba2463400820db5176f`.

## Status, lineage and reuse

**REJECTED for this performance gate:** every measured change. The source with
the reused correction is additionally a **FINITE_COUNTERMODEL** to that
specific composition. The corrected packed evaluator is a **CANDIDATE** for
reuse at its finite tested scope; it is not a new all-input qualification.

The resulting **NAMED_OBSTRUCTION** is
`NO_DEVELOPMENT_GAIN_AT_DECLARED_THRESHOLD`. It rejects these experiments and
does not assert that a faster exact kernel is impossible. Held-out seed
318674905 remains unused. The independently qualified earlier joint source
and the previous hosted score-budget result remain distinct and unchanged.

The same structure appears in the earlier FRET/R2U2 and representation-boundary
work: validating one component does not establish the preconditions required
by the next component. Here it is executable and narrowly evidenced: a guarded
approximation passes its complete-cell checks while its reused fallback fails.
This is a reusable test pattern, not a claim that all such boundaries fail.

The highest-leverage residual remains substantial whole-kernel cost reduction.
Unifying dispatch and reducing arithmetic are insufficient when extra table
bytes, register pressure and fallback frequency erase the savings. The next
experiment should first account for **all three costs on a complete large
family**, then require the existing training and held-out gates before any
expensive whole-domain qualification. The earlier conditional budget still
requires about a one-third instruction cut in central sigmoid or common
negative exp at fixed bytes; that target has not been achieved.

All generated numerical candidates, rejected trials, raw reports, cell records
and native comparisons are preserved in `Conjectures-numerical-continuation-20261126.zip`.
Archive SHA-256:
`d18dc6becf9378a8113f5fb217afbe1a12d9140d864076892e98288a9f11c4e7`;
3,376,842 bytes. CRC and all 395 payload hashes were checked. Version 1 adds
the independent hosted evidence; version 0 is retained as earlier lineage.
Source code,
tests and this report are kept in Git; generated evidence stays outside it.

No registration, payment or contest submission occurred.
