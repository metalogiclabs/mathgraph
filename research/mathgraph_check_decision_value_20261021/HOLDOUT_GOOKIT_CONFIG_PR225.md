# Prospective source-native PR test — target lock 2026-10-21

Target selected by repository and open PR title ONLY, before fetching PR body, diff or source:
- repo: gookit/config
- PR: #225, "Release the write lock before invoking set.value hooks"
- immutable base/head SHA: TO_BE_FILLED_FROM_METADATA_BEFORE_SOURCE_EXPOSURE
- availability: public repository, no third-party writes

## Frozen independent test obligations
Conventional reviewer baseline: source diff reading with Go race detector and existing package suite, plus explicit reasoning about callback reentrancy, lock ordering and concurrent consistency, with identical source/test access.
Candidate: source-independent executable black-box test establishing whether a user callback can synchronously reenter a setter without deadlocking, whether the callback-visible value is already committed, and whether concurrent updates remain safe. A passing result is bounded to tested schedules.
Negative control: hook that does not reenter must continue to work; invalid PR attribution is penalized.
Metric: new consequential issue or correct action missed by equal-information baseline, false issue allegations, execution/cost, independently replayable old/new/head/ablation results.
Required run: original source native test, candidate probe on base and PR head, independently executed negative control; prefer repeated runs/race.
Freeze rule: no change to these hypotheses after inspecting implementation. If infeasible, mark UNKNOWN/INCONCLUSIVE, do not substitute a favorable PR.
No third party communication or mutation. No green CI equals safe merge.
