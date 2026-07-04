# SorryDB v4.2.8 Cache-Get Success Ledger

v4.2.8 records the first successful crossing of the v4.2.4/v4.2.5 cache/build boundary.

## Prior obstruction

v4.2.4 reached real Lean contact with:

    lake env lean MetaExamples/Fiddle.lean

The result was:

    OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY

The failure was:

    unknown module prefix Mathlib
    Mathlib.olean missing

v4.2.5 inspected the repository and found:

    repo exists
    source exists
    lake-manifest exists
    lean-toolchain = leanprover/lean4:v4.22.0
    .lake/packages contains dependencies
    mathlib package exists
    Mathlib.olean missing
    package build lib dirs absent

## Portal

v4.2.6 added an explicitly gated cache-get runner.

v4.2.7 packaged it for disposable execution.

The executed command path was:

    scripts/sorrydb/sorrydb_v4_2_7_disposable_cache_get_runner.sh

which invoked v4.2.6 with:

    SORRYDB_V426_ALLOW_CACHE_GET=1
    SORRYDB_V426_RUN_BASELINE_AFTER_CACHE=1

## Observed result

The disposable run reported:

    CACHE_GET_VERDICT=CACHE_GET_PASSED
    BASELINE_VERDICT=BASELINE_PASSED
    FINAL_VERDICT=BASELINE_PASSED

The cache-get result included:

    lake exe cache get
    returncode = 0
    downloaded 7067 / 7067 file(s)
    100% success
    completed successfully

The follow-up baseline result was:

    lake env lean MetaExamples/Fiddle.lean
    BASELINE_PASSED

## Interpretation

The dependency/cache wall was real and has now been crossed for the pinned MetaExamples replay target.

This does not prove any SorryDB patch.

It proves:

    cached repo + recorded commit + explicit cache-get
    is sufficient to make the unmodified source file pass baseline Lean replay.

## Next obstruction frontier

The next frontier is no longer repo hydration or Mathlib cache availability.

The next frontier is controlled SorryDB patch replay:

    baseline-passing source
    + localized sorry declaration target
    + patch attempt
    + Lean replay
    -> PATCH_ACCEPTED / PATCH_REJECTED / named obstruction

## Bounded claim

v4.2.8 is a result ledger.

It records a successful cache-get and baseline replay crossing.
It does not claim proof repair, accepted patches, or declaration retrieval success.
