# ARC cross-task developmental identity boundary — V21 to V22

This note records the final two prospective attempts to identify a transferable developmental policy above the positive within-episode V19 result.

Pinned source: `fchollet/ARC-AGI@399030444e0ab0cc8b4e199870fb20b863846f34`.

## V21 — defeasible inherited prior

V20c showed that allowing inherited source preferences to outrank current verifier residuals was harmful. V21 therefore froze the corrected ordering

\[
\boxed{
\text{live residual support}
>
\text{live residual diversity}
>
\text{inherited source prior}.
}
\]

The six targets already observed in V20c were excluded. The remaining legal ARC training carriers were split into source and target sets by a stable SHA-256 task-ID parity rule independent of labels and outcomes.

Run: `33149175407`.

Target cohort: 14 disjoint legal carriers.

Exact result:

| arm | exact tasks | total unresolved pairs | total queries |
|---|---:|---:|---:|
| WARM | 13/14 | 1 | 80 |
| COLD | 12/14 | 2 | 84 |
| RAW_HISTORY | 13/14 | 2 | **76** |
| SHAM | 13/14 | 1 | 80 |
| ANCESTOR_ABLATION | 12/14 | 2 | 84 |

There were zero WARM-only exact targets. WARM improved over COLD, but RAW and SHAM reproduced the apparent coverage gain and RAW was cheaper than WARM.

Strict gate: `FAIL_DEFEASIBLE_CROSS_TASK_DEVELOPMENT`.

Interpretation: making inherited experience defeasible removed much of the harm, but a global learned query-shape prior still had no demonstrated causal identity. The apparent gain was compatible with generic tie perturbation.

## V22 — residual-conditioned source policy

The next smallest extension moved the transferable object one level higher. Instead of learning a global preference over query shapes, source episodes produced examples of

\[
\boxed{
\text{anonymous current separator profile}
\to
\text{query-program shape selected by verified residual history}.
}
\]

Source data consisted of all 29 legal ARC training carriers and 162 verifier-driven source examples. At target time, the policy used nearest-neighbour similarity between the current anonymous separator profile and source profiles. Current live residual support and diversity still outranked the inherited conditional vote.

The target was fixed before transfer outcomes were inspected: `60c09cac`, the sole fresh evaluation carrier established mechanically by the exhaustive V20b census.

Five arms used the same eight-query budget. SHAM retained the exact source residual profiles but deterministically permuted the learned selected-query fingerprints across them.

Run: `33149440466`.

Exact result:

| arm | exact target | queries used |
|---|---:|---:|
| WARM residual-conditioned | yes | 7 |
| COLD | yes | 6 |
| RAW_HISTORY | yes | **5** |
| SHAM | yes | 7 |
| ANCESTOR_ABLATION | yes | 6 |

Strict gate: `FAIL_RESIDUAL_CONDITIONAL_CROSS_SPLIT_DEVELOPMENT`.

The WARM and SHAM policies have the same query count, while RAW closes the target two queries sooner than WARM. Therefore the learned residual-conditioned mapping does not have causal transfer identity on the held-out carrier.

## What is now falsified

Under the frozen V17 observation language and V13 one-step future audit, the following should **not** be promoted as domain-general ARC developmental laws:

1. a global source query-shape preference;
2. a global source preference made merely defeasible by current residuals;
3. the tested nearest-neighbour mapping from current anonymous separator profile to source-selected query shape.

V19 remains a valid positive result: within a task, retaining the actual sequence of verifier-returned residuals changes later query selection and closes a protected future quotient that the memoryless policy misses under the same budget.

But

\[
\boxed{
\text{within-episode developmental value}
\not\Rightarrow
\text{cross-episode transferable policy identity}.
}
\]

## Forced next boundary

The repeated transfer failures point above query ranking. The fixed V17 observation language was itself assembled through a source-specific developmental lineage. The next meaningful ARC question is therefore not another prior over those atoms. It is whether residuals can generate or select the **observation-language / meta-constructor** that produces useful distinctions on a new task.

In MSI terms, the likely transferable object must sit above

\[
q\in C_t
\]

and act on the generation of `C_t` itself.

The natural frontier is therefore

\[
\boxed{
\rho
\to
\text{observation-language generator}
\to
C_{t+1}
\to
\Pi_{t+1},
}
\]

with source-distinct transfer and exact ablation.

That experiment requires a new protected constructor boundary. Continuing to tune query preference within the frozen V17 carrier would no longer be residual-licensed.

## Claim boundary

ARC currently establishes:

- verifier-forced representation refinement on natural tasks;
- cumulative retained future-relative interfaces;
- within-episode residual-history-induced developmental policy improvement.

ARC does **not** currently establish a causally identified source-distinct transferable query policy under the tested V17/V13 carrier.

This negative boundary is retained as part of the result rather than hidden by post-hoc target or scoring changes.