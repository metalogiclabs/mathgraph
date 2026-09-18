# Open Math Model × MathGraph — Sustained-Use Evidence Summary V1

## Executive result

Three exact public SAIR Stage 2 probes now separate **useful verified reuse**
from **naive global transfer**.

All runs use the same trusted boundary:

```text
candidate finite magma
→ exact source-law check
→ exact target violation witness
→ promote only verified countermodels
→ later search may reuse/rank them
→ bounded misses remain RESIDUAL, never TRUE
```

The public SAIR source is pinned to commit
`817a4653bf762584931d49c6714c9fcfab7df66a`.

Qualification runs:

- initial official sample-200 evidence:
  https://github.com/metalogiclabs/mathgraph/actions/runs/35394904849
- disjoint normal-set replication and cross-set transfer:
  https://github.com/metalogiclabs/mathgraph/actions/runs/35395349250

## 1. Official sample-200: within-stream verified reuse helps

Frozen before the successful result:

- 100 TRUE / 100 FALSE official sample problems;
- first 25 FALSE tasks: acquisition;
- remaining 75 FALSE tasks: untouched fresh evaluation;
- exact candidate universe: all 16 size-2 magma tables.

Acquisition produced 8 distinct verifier-backed capabilities.

| condition | fresh finite countermodels | fresh residuals | verifier calls |
| --- | ---: | ---: | ---: |
| cold | 61 | 14 | 464 |
| warm | 61 | 14 | 397 |
| restart | 61 | 14 | 397 |
| sham | 61 | 14 | 581 |
| ablation | 61 | 14 | 471 |

Observed:

- **14.44% fewer verifier calls** on the fresh set;
- **1.169×** cold/warm search compression;
- exact terminal yield preserved at **61/75 = 81.33%**;
- restart reproduced warm exactly;
- sham cost 184 more calls than warm;
- ablation cost 74 more calls than warm;
- all 100 TRUE controls × all 16 tables produced 0 countermodels.

Including acquisition, total calls fell from **594 → 527**, an **11.28%**
full-sequence reduction.

## 2. Disjoint normal-set replication: the effect gets larger

A second policy was committed before its result was inspected.

To separate it from the first probe, every exact `(eq1_id, eq2_id)` pair in
`sample_200` was excluded from public `normal.jsonl`.

Remaining public normal set:

- 500 FALSE;
- 500 TRUE;
- first 100 FALSE: acquisition;
- remaining 400 FALSE: fixed fresh evaluation.

Acquisition produced 9 distinct verifier-backed capabilities.

| condition | fresh finite countermodels | fresh residuals | verifier calls |
| --- | ---: | ---: | ---: |
| cold | 361 | 39 | 1967 |
| warm | 361 | 39 | 1501 |
| restart | 361 | 39 | 1501 |
| sham | 361 | 39 | 2686 |
| ablation | 361 | 39 | 2963 |

Observed:

- **23.69% fewer verifier calls** on the fresh set;
- **1.310×** cold/warm search compression;
- exact terminal yield preserved at **361/400 = 90.25%**;
- restart reproduced warm exactly;
- sham cost 1185 more calls than warm;
- ablation cost 1462 more calls than warm;
- all 500 TRUE controls × all 16 tables produced 0 countermodels.

Including acquisition, total calls fell from **2413 → 1947**, a **19.31%**
full-sequence reduction.

## 3. Cross-set transfer: verified does not mean universally useful

The third probe deliberately gave the normal set **no target-side acquisition**.

It learned the 8 capabilities only from the first 25 FALSE problems of
`sample_200`, then transferred that frozen ordering to all 500 disjoint normal
FALSE tasks.

| condition | finite countermodels | residuals | verifier calls |
| --- | ---: | ---: | ---: |
| cold | 452 | 48 | 2413 |
| transferred warm | 452 | 48 | 2475 |
| restart | 452 | 48 | 2475 |
| sham | 452 | 48 | 3172 |
| ablation | 452 | 48 | 3306 |

The transferred verified bank was **2.57% worse than cold** on target search.
Including its original source-acquisition cost, it was **2.44% worse** overall.

This negative result is important. It rules out the stronger story that a
verified capability should simply be promoted globally because it was useful in
one source stream.

## What the three probes jointly say

The supported statement is narrower:

> **Verified mathematical artifacts can reduce later verifier-directed search,
> but usefulness is contextual. Verification licenses truth of the artifact;
> it does not license universal priority or universal transfer.**

That creates a concrete developmental requirement:

```text
verify
→ retain
→ attach scope / consequence evidence
→ reuse where licensed
→ gather target-local evidence
→ rerank / revoke when transfer stops paying
```

In other words, the next useful layer is not a bigger global cache. It is a
**scoped capability controller** that distinguishes:

- authority: is the mathematical artifact actually valid?
- relevance: is it useful in this target regime?
- economics: does reusing it reduce sustained verification cost?
- lifecycle: should its priority be retained, reduced, scoped, or revoked?

That is the precise place where the QCKN-style causal ledger, scope, promotion,
restart and revocation machinery can become operational rather than rhetorical.

## Claim boundary

These results are:

- exact and reproducible;
- on public SAIR Stage 2 development data;
- bounded to the complete 2-element magma universe;
- verifier-call/search-order results.

They are **not**:

- LLM results;
- token-cost or wall-time results;
- private SAIR evaluation results;
- evidence that larger carriers behave the same way;
- evidence that the percentages generalize to the future SAIR Open Math Model.

The model-facing transcript harness in this branch is the next boundary: once a
real model is run through the frozen cold/warm/sham/ablation/restart prompts,
provider-reported tokens and latency can be evaluated under the same
independent-verification discipline.
