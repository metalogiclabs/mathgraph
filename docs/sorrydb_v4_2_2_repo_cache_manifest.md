# SorryDB v4.2.2 Repo-Cache Manifest Mode

v4.2.2 adds a dry-run replay manifest mode for the SorryDB declaration-retrieval patcher.

It does not run Lean, Lake, Git, `lake update`, `lake exe cache get`, baseline checks, or patch attempts when manifest mode is enabled.

## Purpose

The previous boundary after v4.2.1 was `OBSTRUCTED_MISSING_FILE`: native SorryDB records could be selected safely, but local replay source files were absent after cleanup. v4.2.2 turns that into a concrete replay manifest: which repository, commit, file, and source path would be required before any expensive hydration is attempted.

## Environment

- `SORRYDB_V422_DRY_RUN_MANIFEST=1`
- `SORRYDB_V422_REPO_CACHE_ROOT=/path/to/repo_cache`

The cache key is derived from repository URL and commit.

## Manifest

The run writes `replay_manifest.jsonl`, with rows containing:

- `repo`
- `commit`
- `lean_version`
- `file_path`
- `line`
- `statement`
- `expected_repo_cache_path`
- `expected_source_path`
- `repo_cached`
- `source_exists`
- `obstruction`

Possible dry-run obstructions:

- `OBSTRUCTED_REPO_NOT_CACHED`
- `OBSTRUCTED_MISSING_FILE`
- `NONE`

## Bounded claim

v4.2.2 prepares cache-aware replay manifests. It does not claim proof repair, Lean replay success, repo hydration, or accepted patches.
