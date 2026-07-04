# SorryDB v4.3.7 Streaming Queue Runner

## Purpose

v4.3.7 resolves the operator-visibility obstruction recorded by the v4.3.6
enabled queue reality ledger. The JSON patch queue runner now reports each
candidate as it starts and completes, records its certificate identifier, and
writes `partial_queue_run_summary.json` after every completed candidate.

The queue format and final `queue_run_summary.json` remain compatible with
v4.3.5. Default safety is unchanged: `SORRYDB_V435_ALLOW_RUN=0` produces
`QUEUE_RUN_DISABLED` and does not execute candidates.

## Optional child output streaming

Set `SORRYDB_V435_STREAM_CHILD_OUTPUT=1` to relay child stdout and stderr with
candidate prefixes. The default is false. Whether streamed or not, only bounded
stdout and stderr tails are retained in result objects.

An interrupted enabled run records `QUEUE_RUN_INTERRUPTED` when possible and
preserves completed results in the partial summary. During normal execution,
the partial verdict is `QUEUE_RUN_IN_PROGRESS`; the final verdict remains
`QUEUE_RUN_COMPLETED` or `QUEUE_RUN_COMPLETED_WITH_FAILURES`.

## Bounded claim

Queue execution is more observable and interruption-tolerant. This artifact
does not claim general proof repair, arbitrary SorryDB automation, declaration
retrieval success, multi-file patching, or upstream submission. Interruption
during a child replay remains a known source-restoration obstruction owned by
the controlled replay boundary.

## Next frontier

Run a controlled 10–20 candidate queue, or mine candidates automatically from
exact-source SorryDB rows, without weakening exact-source replay admission.
