# SorryDB v4.2.7 Disposable Cache-Get Execution Plan

v4.2.7 adds a disposable shell runner for executing the v4.2.6 cache-get portal outside the normal laptop worktree.

It is intended for Colab, CI, or disposable local storage.

It:
- creates an isolated work root under /tmp by default
- clones MathGraph
- checks out the requested MathGraph ref
- clones MetaExamples
- checks out the recorded SorryDB commit
- runs v4.2.6 with SORRYDB_V426_ALLOW_CACHE_GET=1
- reruns baseline only after cache-get succeeds
- prints cache_get_manifest.json and final verdicts

It does not:
- patch proofs
- perform declaration retrieval
- run lake update
- mutate the main local worktree

Default target:
- repo: https://github.com/siddhartha-gadgil/MetaExamples.git
- commit: edbb75e784db19846a1c19841e182b797afc18bb
- file: MetaExamples/Fiddle.lean

Bounded claim:
v4.2.7 packages the controlled cache-get experiment for disposable execution.
It does not claim cache-get, baseline, or proof success unless the emitted v4.2.6 manifest says so.
