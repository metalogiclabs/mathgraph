# SorryDB v4.2.6 Cache-Get Boundary Runner

v4.2.6 adds a gated cache-get boundary runner.

Default behavior is safe:
- cache-get is disabled unless SORRYDB_V426_ALLOW_CACHE_GET=1
- lake update is always forbidden
- git clone, git fetch, git checkout, curl, wget, sudo, and rm -rf are forbidden
- patch attempts and declaration retrieval are not performed

Purpose:
cross the v4.2.5 boundary only when explicitly allowed.

It can run:
    lake exe cache get

Then optionally:
    lake env lean <file>

Outputs:
    cache_get_manifest.json

Verdicts include:
- CACHE_GET_DISABLED
- CACHE_GET_PASSED
- CACHE_GET_FAILED
- OBSTRUCTED_DISK_PRESSURE
- OBSTRUCTED_REPO_MISSING
- OBSTRUCTED_SOURCE_MISSING
- OBSTRUCTED_UNSAFE_COMMAND
- OBSTRUCTED_CACHE_GET_TIMEOUT
- BASELINE_PASSED
- OBSTRUCTED_BASELINE_TIMEOUT
- OBSTRUCTED_BASELINE_COMPILE_FAILURE
- OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY

Bounded claim:
v4.2.6 provides a controlled cache-get portal and records what happens.
It does not claim proof repair, accepted patches, or dependency success unless the external command actually succeeds.
