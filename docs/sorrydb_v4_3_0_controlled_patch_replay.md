# SorryDB v4.3.0 Controlled Patch Replay

v4.3.0 begins the next frontier after cache-get and baseline replay succeeded.

Prior landed result:

    CACHE_GET_VERDICT=CACHE_GET_PASSED
    BASELINE_VERDICT=BASELINE_PASSED
    FINAL_VERDICT=BASELINE_PASSED

This means the current wall is no longer repository hydration or Mathlib cache availability.

The new frontier is controlled patch replay:

    baseline-passing source
    + one localized sorry target
    + one explicit replacement
    + Lean replay
    -> PATCH_ACCEPTED / PATCH_REJECTED / named obstruction

Default safety:

    SORRYDB_V430_ALLOW_PATCH=0

With patch disabled, the runner emits:

    PATCH_DISABLED

and does not mutate the source file or run Lean.

When enabled, it can:
- optionally run a baseline first
- apply exactly one text replacement
- run lake env lean <file>
- restore the original source file
- emit patch_replay_manifest.json

Forbidden:
- lake update
- lake exe cache get
- git clone/fetch/checkout
- curl/wget
- sudo
- rm -rf
- declaration retrieval
- multi-target patching

Default target:

    theorem eg₁ (n : ℕ) : n ≤ n + 1 := sorry

Default patch:

    theorem eg₁ (n : ℕ) : n ≤ n + 1 := by exact Nat.le_succ n

Bounded claim:

v4.3.0 adds a controlled patch replay portal.
It does not claim any patch was accepted unless the emitted manifest reports PATCH_ACCEPTED.
