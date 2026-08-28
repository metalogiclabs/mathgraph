# ARC developmental transfer boundary — V20 to V20c

Pinned source: `fchollet/ARC-AGI@399030444e0ab0cc8b4e199870fb20b863846f34`.

This note records the first prospective attempts to transfer the residual-history developmental policy learned in V19 across source-distinct ARC episodes. The negative results are retained as constraints on the developmental claim.

## V20 — prospective evaluation-to-evaluation transfer

Source episodes were the four frozen V13–V19 evaluation tasks. Their verifier-returned residual histories were compressed into scores over mechanically anonymized executable observation-program fingerprints: demo, row and column indices were erased while opcode/relation structure was preserved.

Target selection was precommitted before the run: scan fresh evaluation task IDs lexicographically, exclude source IDs, and take the first six tasks satisfying all of:

1. a nontrivial protected one-step future split;
2. full V17 cumulative observation-language sufficiency on demo and held-out labels;
3. no continuation-search truncation.

Five matched arms were specified: WARM, COLD, RAW_HISTORY, SHAM and ANCESTOR_ABLATION, all with an eight-query budget.

Run: `33148416085`.

Result: the first 80 fresh evaluation tasks contained **zero legal target carriers**. Therefore the causal policy comparison was not instantiated and the strict gate failed.

This is not evidence against the policy by itself. It exposed a transfer-boundary question in the protected future definition / observation carrier.

## V20b — full evaluation-set boundary census

Rather than relaxing the target criterion, V20b exhaustively audited all 396 remaining evaluation tasks.

Run: `33148573621`.

Exact summary:

- tasks audited: **396**;
- no continuation truncation: **396**;
- tasks with a nontrivial protected future split: **1**;
- tasks whose full V17 language exactly represents both demo and held-out future quotient: **1**;
- sole legal carrier: `60c09cac`.

Decision: `V17_LANGUAGE_HAS_FRESH_TRANSFER_CARRIER`.

The sharper interpretation is that the main sparsity was not V17-language failure: under the frozen one-step future audit only one fresh evaluation task generated a nontrivial developmental classification problem at all, and that one was representable by V17.

The lone carrier was **not** used post hoc as a positive transfer test.

## V20c — prospective evaluation-to-training split

To obtain a genuinely untouched target family, the source policy remained frozen from the same four evaluation episodes while targets came from the ARC training split.

Before inspecting target outcomes, target selection was fixed to the lexicographically first six legal training carriers under the same exact criteria. The selector scanned 106 tasks and selected:

- `0d3d703e`
- `1cf80156`
- `28bf18c6`
- `3af2c5a8`
- `3c9b0459`
- `46442a0e`

Run: `33148954261`.

Exact task coverage under the eight-query budget:

| arm | exact tasks | total unresolved future-conflicting pairs |
|---|---:|---:|
| WARM | 4/6 | 17 |
| COLD | 5/6 | 2 |
| RAW_HISTORY | 4/6 | 9 |
| SHAM | 5/6 | 1 |
| ANCESTOR_ABLATION | 5/6 | 2 |

There were **zero WARM-only exact targets**. The strict cross-split developmental-compounding gate failed.

The strongest failure was on `0d3d703e`: WARM left 16 unresolved pairs, COLD left 2, while SHAM reached the exact quotient.

## What the negative result forces

V20c ranked inherited source experience ahead of the current target episode's accumulated residual history. The result falsifies that ordering as a domain-general developmental rule.

The smallest justified correction is:

\[
\boxed{
\text{current verified residual evidence}
\succ
\text{inherited developmental prior}.
}
\]

Inherited experience may guide a choice only after satisfying the distinctions forced by the current protected future. A developmental prior must therefore be defeasible.

This gives a more precise MSI retention principle:

> Prior development may break ties among futures still equivalent under current evidence; it may not override a distinction the current verifier has already forced.

## Claim boundary

V19 remains a positive within-episode result: retained verifier residual history changed later question selection and closed a task the memoryless policy did not close under the same budget.

V20/V20c show that this does **not** automatically imply cross-episode transfer. In particular, a policy estimated from four source tasks and promoted above live residual evidence is not a transferable developmental law.

The next test is V21: exclude the six V20c targets, split the remaining legal training carriers by a stable task-ID hash, learn only on the source half, and rank target queries by

\[
\boxed{
\text{live residual support}
>
\text{live residual diversity}
>
\text{inherited source prior}.
}
\]

That test changes only the causal ordering forced by V20c; it does not add a new observation language or semantic ARC feature.