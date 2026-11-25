# RISC-V frontier continuation — 25 November 2026

**Outcome: no new competitive candidate.** Twenty-eight fixed source changes were tested against the retained RRR source. None reduced its score on both the recorded champion input draw and the held-out draw. No registration, payment, signing, entry submission or production-branch modification occurred.

Retained source SHA-256: `3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4`.

| Quantity | Recorded champion seed 1284956104 | Held-out seed 20261219 |
| --- | ---: | ---: |
| Retained RRR RV32IM S | 29.149320828872046 | 29.22505188402248 |
| Published predecessor #47 S | 29.16534683309135 | 29.180230228094942 |
| Current #52 takeover threshold on recorded inputs | 27.338009176634163 | Unknown on these fresh inputs |

The retained candidate needs a further **6.213906879%** score reduction on the recorded inputs. A future official submission would remeasure both candidates on new inputs; this is not a takeover verdict.

## Recovered public evidence

[Run 45571639026](https://github.com/metalogiclabs/mathgraph/actions/runs/45571639026), workflow `1dc9bb223d8866b84b56541bef2e3dcdb32a162f`, recovered published former champions #47, #45 and #40, checked each file against its official report digest, and measured their unchanged files plus RRR on both seeds. Current board reference remained #52, promotion 59. All local/live measurement identities and recorded input digests agree.

- #47: `bd2b39b11a3756c7545fc8b56cadabcb150acb6b8465842985363404c45dfd42`.
- #45: `63e2b699effd10efca8f930384218c8945e12c56b2738e99e62fc027e68261e3`.
- #40: `c199002ef13611f2ceb3447e2d047b89eb8c4d44ee11bccd006ad101527b74e8`.

Predecessor #47's exponential is individually cheaper; RRR's sigmoid and tanh are individually cheaper. Composition does not inherit that apparent advantage.

## Completed experiments

| Family | Changes, excluding control | Run | Result |
| --- | ---: | --- | --- |
| Exact coefficient layouts, immutable banks, exponent predicates | 10 | [45572430701](https://github.com/metalogiclabs/mathgraph/actions/runs/45572430701) | Six ties, four slower; 11 measurement jobs passed |
| Fixed portable predecessor composition | 3 | [45572601127](https://github.com/metalogiclabs/mathgraph/actions/runs/45572601127) | Portable predecessor trades off the two draws; isolated mix slower; shared mix rejected by AST cycle rule |
| Exact nonzero-table and even-product invariant elimination | 6 | [45573434044](https://github.com/metalogiclabs/mathgraph/actions/runs/45573434044) | All six slower; seven measurement jobs passed |
| Return-site alternatives under the same unreachable-site certificate | 9 | [45574056518](https://github.com/metalogiclabs/mathgraph/actions/runs/45574056518) | Three ties, six slower; ten measurement jobs passed |

The first layout run [45572210506](https://github.com/metalogiclabs/mathgraph/actions/runs/45572210506) failed before testing because the repository already contained an evidence directory. The corrected workflow uses a separate output path. Preserve this as an apparatus failure, not a numerical rejection.

All 32 native differential stages passed **9,582,336 comparisons each**, totaling **306,634,752** baseline/candidate output comparisons across pseudorandom inputs and exponent/cell boundaries. Of 32 official measurement jobs, 31 passed; the shared composition was rejected before measurement by the actual recursion policy. These are bounded comparisons and official samples, not a new exhaustive correctness proof.

All full-qualification gates correctly stayed closed because no change achieved the declared >=0.5% paired gain. The earlier joint candidate's exhaustive qualification remains retained.

## Source-relative certificates and causal finding

RRR's only three `tld_r` rows with `c1 == 0` are 28, 60 and 95. Exact integer high-multiply bounds confine their remainder magnitudes to 18,691, 4,976 and 17,450, respectively. Their nonzero constants are 361,307,905; 1,487,863,553; and 2,481,618,689. Therefore their computed V cannot equal zero.

An independent native enumeration checked every word and both signs in those cells: **1,572,864 cases, zero zero-values**. Each row's actual values are its c0 or c0-1. Two deliberate zero-cell/table perturbations were rejected by the certificates. Published #47's 256-word exponential table is also entirely nonzero, and its aligned index is always in 0..255. The unsigned product `w*(w+1)` is even modulo 2^32, so three masked pointer offsets are exactly zero.

These facts legitimately remove an unreachable call edge and resolve the shared composition's AST cycle. They do **not** imply a performance gain: removing RRR's impossible tanh return increased S from 29.1493 to 32.3413. The cleaned shared mix passed the gate but scored 29.4835. The evidence establishes compiled-cost sensitivity to source/call structure on these programs, not a new general compiler theorem.

Replay the certificates and falsifiers with:

```bash
python research/eik/rv_invariant_replay.py retained-rrr.c published-entry-47.c
```

The script checks both source hashes before compiling and enumerating the cells. Generators, differential harness and replay script are retained on `research/eik-rv-frontier-20261125`.

## Integrity, selection and residual

Independently downloaded and SHA-256/CRC checked **37 experiment archives, 233 files**. Reconstructed every layout, invariant and call-structure source exactly from its pinned parents. Both seed input digests and measurement identities match within each admitted comparison.

The layout selector chose `all-reverse` on a zero-gain tie; its qualification flag remained false. This is not a promotion. Retain the original RRR source explicitly. The invariant and final call-structure selectors also found zero gain; the final selector retained the original control.

**Named bounded obstruction: NO_PAIRED_GAIN_IN_28_FIXED_VARIANTS.** This rejects only these concrete transformations, not the existence of a better kernel. The high-leverage residual remains numerical representation: reduce work in the common cell evaluator while preserving its rounding boundary and charging the complete code/table-size penalty. The smallest useful next experiment should target one complete mathematical cell family with a genuinely different arithmetic representation; do not repeat the tested layouts, source simplifications or predecessor mix under new names.
