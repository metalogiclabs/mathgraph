# Open Math Model × MathGraph — SAIR Official Sample-200 Reuse Evidence V1

## Result

A fixed, pre-result bounded reuse policy was run against the official public
SAIR Stage 2 `sample_200.json`, pinned to:

- repository: `SAIRcompetition/equational-theories-lean-stage2`
- commit: `817a4653bf762584931d49c6714c9fcfab7df66a`
- MathGraph branch: `open-math-model-sustained-use-v1`
- qualification run: https://github.com/metalogiclabs/mathgraph/actions/runs/35394904849
- evidence artifact: `sair-official-sample200-bounded-reuse-v1`

The policy was committed before the successful sample-200 run. The only change
after the first failed attempt was a data-loader correction: the official
`sample_200.json` already contains its own `answer` field, so the runner now
reads that field directly instead of attempting to join unrelated
normal/hard IDs. The acquisition split, finite universe, promotion rule,
warm ordering, sham ordering, ablation ordering, and fresh set were unchanged.

## Frozen protocol

The official sample contains 100 TRUE and 100 FALSE implications.

For the FALSE side:

- acquisition: first 25 FALSE problems in official sample order;
- fresh evaluation: remaining 75 FALSE problems;
- candidate universe: all 16 binary operation tables on carrier `{0,1}`;
- cold order: lexicographic table index;
- promotion: independently verified finite countermodels found during acquisition;
- exact-table deduplication;
- warm order: promoted tables ranked only by acquisition support, then all
  remaining tables in cold order;
- restart: serialize and reload the capability bank before reconstructing the
  same warm order;
- sham: a fixed alternating high/low table order independent of acquisition
  evidence;
- ablation: move all promoted tables behind all non-promoted tables.

Every condition checks the same complete set of 16 tables. Only the order
changes. Therefore a search-order gain cannot change the bounded terminal
outcome.

For the TRUE side, all 16 size-2 tables are checked as a contamination control.
No failed finite search is ever promoted to TRUE.

## Observed evidence

Acquisition produced **8 distinct independently verified size-2 capabilities**.

On the untouched 75 FALSE problems:

| condition | finite countermodels | residuals | verifier calls | mean calls |
| --- | ---: | ---: | ---: | ---: |
| cold | 61 | 14 | 464 | 6.187 |
| warm | 61 | 14 | 397 | 5.293 |
| restart | 61 | 14 | 397 | 5.293 |
| sham | 61 | 14 | 581 | 7.747 |
| ablation | 61 | 14 | 471 | 6.280 |

Thus:

- warm verifier-call reduction vs cold: **14.44%**;
- cold/warm compression: **1.169×**;
- restart reproduces warm exactly;
- sham costs **184 more verifier calls** than warm;
- ablation costs **74 more verifier calls** than warm;
- all five conditions preserve exactly the same bounded terminal yield:
  **61/75 = 81.33%**;
- all 100 official TRUE controls were checked against all 16 size-2 tables and
  produced **0 finite countermodels**.

Including acquisition cost, the complete acquisition + fresh sequence uses:

- cold baseline: **594 verifier calls**;
- developmental reuse: **527 verifier calls**;
- reduction: **11.28%**.

Of the 61 fresh finite-countermodel recoveries under the warm ordering, 60 end
at one of the promoted table identities. This is a narrow but direct form of
verified capability reuse.

## Capability bank

The eight promoted table identities, ordered by acquisition support, are:

| table index | acquisition support | table |
| ---: | ---: | --- |
| 6 | 10 | `[[0,1],[1,0]]` |
| 5 | 9 | `[[0,1],[0,1]]` |
| 2 | 6 | `[[0,0],[1,0]]` |
| 4 | 6 | `[[0,1],[0,0]]` |
| 3 | 5 | `[[0,0],[1,1]]` |
| 1 | 3 | `[[0,0],[0,1]]` |
| 0 | 2 | `[[0,0],[0,0]]` |
| 8 | 1 | `[[1,0],[0,0]]` |

These are not model-generated beliefs or route scores. Each was promoted only
after the finite checker established a concrete source-satisfying,
target-violating witness during acquisition.

## What this establishes

Within this exact bounded world, independently verified mathematical artifacts
can be retained, restarted, and reused on untouched official SAIR tasks to
reduce later verifier-directed search without changing correctness or the
terminal boundary.

The sham and ablation controls distinguish the observed gain from merely having
a memory object or from changing the number of candidates examined.

## What this does not establish

This is **not**:

- an LLM result;
- a token-cost or wall-time result;
- a claim that 2-element magmas are sufficient for SAIR Stage 2;
- a proof for the 14 fresh residuals;
- a claim about all SAIR problems;
- evidence that the same percentage will hold for SAIR's future Open Math
  Model.

It is a public, replayable first test of the narrower sustained-use hypothesis:
verified mathematical work can become causally useful state for later
verification.

## Reproduce

```bash
git checkout open-math-model-sustained-use-v1

python scripts/run_sair_official_sample200_reuse_probe.py \
  --out-dir /tmp/sair-official-sample200-reuse-v1
```

The runner pins the official SAIR source commit, records source hashes, emits
the full split and per-problem rows, serializes the verified capability bank,
and writes both `report.json` and `report.md`.
