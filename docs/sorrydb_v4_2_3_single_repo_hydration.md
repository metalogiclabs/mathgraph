# SorryDB v4.2.3 Single-Repo Hydration Manifest

v4.2.3 adds a bounded single-repository hydration step for SorryDB replay preparation.

It clones at most one GitHub HTTPS repository into an explicitly supplied cache path, fetches the recorded commit, checks out that commit detached, and writes `hydration_manifest.json`.

It does **not** run Lean, Lake, `lake update`, `lake exe cache get`, baseline replay, declaration retrieval, or patch attempts.

## Environment

- `SORRYDB_V423_REPO`
- `SORRYDB_V423_COMMIT`
- `SORRYDB_V423_CACHE_PATH`
- `SORRYDB_V423_WORK_ROOT`
- `SORRYDB_V423_MIN_FREE_GB`
- `SORRYDB_V423_TIMEOUT_SECONDS`

## Verdicts

- `HYDRATED_REPO_AT_RECORDED_COMMIT`
- `OBSTRUCTED_DISK_PRESSURE`
- `OBSTRUCTED_UNSAFE_REPO_URL`
- `OBSTRUCTED_REPO_NOT_CACHED`
- `OBSTRUCTED_GIT_FAILURE`

## Bounded claim

v4.2.3 hydrates one repo cache entry at a recorded commit and records the result. It does not claim proof repair, Lean replay success, dependency hydration, or accepted patches.
