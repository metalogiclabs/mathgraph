# SorryDB v4.2.5 Cache/Build Boundary Inspector

v4.2.5 inspects an already hydrated SorryDB repository after a baseline replay obstruction.

It does not run Lean, Lake, Git, lake update, lake exe cache get, dependency builds, declaration retrieval, or patch attempts.

Purpose:
turn OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY into a more precise state description.

It checks:
- repo exists
- source exists
- lean-toolchain
- lake-manifest.json
- lakefile.lean or lakefile.toml
- .lake/packages
- package build lib directories
- Mathlib.olean presence

Expected finding after the MetaExamples smoke:
- dependencies were cloned/materialized
- mathlib package exists
- Mathlib.olean is absent
- next safe portal is cache-get or build in a disposable environment, not proof repair

Bounded claim:
v4.2.5 classifies cache/build boundary state from local files only.
It does not claim baseline success, dependency hydration success, proof repair, or accepted patches.
