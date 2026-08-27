# ARC-AGI-2 live developmental-navigation test — precommit

Source is the public ARC-AGI-2 repository pinned at commit `f3283f727488ad98fe575ea6a5ac981e4a188e49`.

This experiment is intentionally prospective with respect to the 120 public evaluation tasks: the routing policy is learned only from the 1,000 public training tasks. Evaluation-task test outputs are used only after a prediction has been selected, for scoring.

## Frozen candidate language

Base families:

1. geometric symmetries;
2. direct color relabeling;
3. crop by one color;
4. crop by complement of one candidate background color;
5. cell replication;
6. whole-grid tiling;
7. uniform-block downsampling.

The developmental extension is one new family only: `geometry_then_recolor`. It is admitted only after the entire base language fails to fit every demonstration pair of a task.

## Frozen comparison

`GLOBAL` learns one family order from the ARC-AGI-2 training set.

`VDN` retains a coarse residual signature of the demonstration relation (dimension relation, color-count relation, train-example count) and learns a signature-conditioned family order, with the global order as backoff. Both arms use exactly the same candidate generators, exact-fit verifier, stopping rule, and evaluation tasks.

## Deciding measurements

Primary navigation measurements on the 120 evaluation tasks:

- exact task solve count;
- total and median number of candidate programs verified before commitment;
- the same search-cost comparison restricted to tasks solved by both arms.

A bounded navigation advantage is recorded only if VDN does not reduce exact solve count and reduces verifier search cost on the common-solved set.

A bounded developmental phase change is recorded only if `geometry_then_recolor`, invoked strictly as a fallback after base exhaustion, exactly solves at least one evaluation task that the frozen base language cannot solve. Because the extension is fallback-only, any base-reachable prediction is preserved by construction.

No claim is made about ARC generally, private test sets, or completeness of the candidate language. A negative result is evidence about this frozen language and routing representation.