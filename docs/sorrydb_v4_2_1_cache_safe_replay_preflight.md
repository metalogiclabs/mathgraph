# SorryDB v4.2.1 Cache-Safe Replay Preflight

This patch is a safety and observability upgrade for the SorryDB declaration-retrieval patcher.

It does not claim LeanLangur success, TheoremGraph retrieval correctness, or improved proof repair. It only bounds replay risk and preserves obstruction evidence.

## Boundary closed

v4.2 reached real external replay contact: native SorryDB records can be adapted into replay targets, focus repositories can be selected by short name or full URL, and local source files can be resolved.

The new obstruction was replay metabolism: historical Lean repositories can hydrate large dependency graphs, drift toolchains if `lake update` is used, fill mathlib caches, and exhaust disk before proof search begins.

## v4.2.1 contract

- Check free disk space before external replay.
- Default minimum free space is 15 GiB.
- `SORRYDB_V421_MIN_FREE_GB` may override the threshold.
- Never run `lake update` inside historical replay.
- Do not run `lake exe cache get` unless `SORRYDB_V421_ALLOW_CACHE_GET=1`.
- Classify failed baselines without cache-get permission as `OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY`.
- Kill Lean/Lake process groups on timeout.
- Write partial artifacts on `KeyboardInterrupt`.
- Baseline-check each target file once per run.
- Keep proof-repair claims bounded to accepted exact-line replay only.

## Historical replay rule

A SorryDB replay must use the recorded commit, manifest, and toolchain. Running `lake update` changes the world being replayed and invalidates the historical claim boundary.
