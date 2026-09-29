# TaskSAT Crystal optional-zone audit v1

## Objective

Audit whether TaskSAT's SMT zone encoding preserves the documented semantics of optional tasks.

Pinned upstream authority:

- `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`

## Declared semantic contract

TaskSAT's theory states that a schedule assigns start/end times to required tasks and to a **subset** of optional tasks, and that all constraints belonging to an optional task are guarded by its inclusion Boolean.

The current encoder instead allocates `2 * len(all_scheduled_tasks) + 2` strictly increasing zone boundaries and aligns **every** task start/end to an internal zone, without guarding zone membership by inclusion.

## Cheapest decisive experiment

The hosted audit runs two exact ablations.

1. **Completeness witness.** Horizon 2 with no tasks is SAT. Adding one excludable optional task makes the fixed four-boundary skeleton impossible over integer time, so the current encoding is UNSAT even though the documented semantics can exclude the task.
2. **Consequence witness.** At horizon 3 an optional task is forced excluded by an impossible start range, yet its unconstrained start/end still force zones `[0,1,2,3]`. The hard temporal constraint `always not (time = 1)` is SAT without the task and UNSAT with the excluded declaration.

The second witness shows this is not merely a small-horizon implementation precondition: an absent task changes the temporal observation structure and therefore a logical verdict.

## Promotion boundary

Before the hosted run completes this is **CANDIDATE**. Promote only if the pinned upstream commit reproduces all declared assertions unchanged.

If reproduced, the smallest residual is not "fix optional tasks" in general. It is:

> Make the zone carrier inclusion-sensitive, or prove a quotient that removes boundaries of excluded tasks while preserving all admitted temporal observations.

No upstream issue or PR is created by this experiment.
