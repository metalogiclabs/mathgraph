# SorryDB v4.2.4 Baseline-Only Replay Manifest

v4.2.4 adds a bounded baseline-only replay step for a single cached SorryDB source file.

It runs only:

    lake env lean <file>

inside an already hydrated repository.

It does not patch files, run declaration retrieval, run lake update, run lake exe cache get by default, clone repositories, fetch repositories, or attempt proof repair.

## Environment

- SORRYDB_V424_REPO_ROOT
- SORRYDB_V424_FILE_PATH
- SORRYDB_V424_WORK_ROOT
- SORRYDB_V424_MIN_FREE_GB
- SORRYDB_V424_TIMEOUT_SECONDS
- SORRYDB_V424_ALLOW_CACHE_GET

## Verdicts

- BASELINE_PASSED
- OBSTRUCTED_DISK_PRESSURE
- OBSTRUCTED_SOURCE_MISSING
- OBSTRUCTED_REPO_MISSING
- OBSTRUCTED_UNSAFE_COMMAND
- OBSTRUCTED_BASELINE_TIMEOUT
- OBSTRUCTED_BASELINE_COMPILE_FAILURE
- OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY

## Bounded claim

v4.2.4 runs a single baseline-only Lean replay for an already cached source file and records the result as baseline_manifest.json.

It does not claim proof repair success, dependency hydration success, or accepted patches.
