# SorryDB v4.4.2 Miner Coverage Profiler

## Purpose

v4.4.2 profiles candidate-supply bottlenecks for the exact-source queue miner. It recursively inventories checked-in replay manifests and patch certificates, groups duplicate evidence by certificate identity, and classifies each potential evidence row as mineable or blocked.

The profiler turns scaling failure into explicit named obstruction categories: missing evidence partners, rejected replay evidence, manifest/certificate disagreement, unavailable source text, non-unique source matches, malformed JSON, and known-span failures.

## Inputs and outputs

The default run reads only checked-in SorryDB artifacts from v4.3.2 through v4.4.1. It writes:

- `artifacts/sorrydb/miner_coverage_v4_4_2/summary.json`
- `artifacts/sorrydb/miner_coverage_v4_4_2/profile.json`

`summary.json` contains stable category counts and the next frontier. `profile.json` retains candidate rows, `NAMED_OBSTRUCTION` rows, duplicate groups, scanned paths, and missing input directories.

Missing directories and malformed JSON do not crash the run. Missing directories are recorded as notes; malformed inputs become `UNCLASSIFIED_OBSTRUCTION` entries.

## Boundary

This is JSON, file, and source-text analysis. It does not invoke Lean, Lake, Git replay, or network services. Its output is not a Lean certificate and does not discover new proofs.

Bounded claim: the profiler identifies which evidence rows are mineable and which are blocked by named obstruction categories.

It does not claim:

- new proof discovery;
- Lean replay success;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

Either ingest broader accepted evidence with exact source provenance, or generate a controlled 10–20 row queue from profiled candidates.
