# SorryDB v4.3.8 Streaming Reality Ledger

v4.3.8 records a real Lean-contact run of the v4.3.7 streaming queue runner.

The run used the two known accepted exact-source patch candidates with:

    SORRYDB_V435_ALLOW_RUN=1
    SORRYDB_V435_STREAM_CHILD_OUTPUT=1

## Result

    STREAMING_REALITY_PASSED

Observed:

    queue verdict: QUEUE_RUN_COMPLETED
    candidate_count: 2
    accepted_count: 2
    failed_count: 0
    partial_summary_count: 1
    manifest_count: 2
    certificate_count: 2
    line 97 restored to sorry
    line 99 restored to sorry

## Candidates

1. metaexamples-fiddle-line97-eg1

    manifest_verdict: PATCH_ACCEPTED
    patch_certificate_id: sorrydb-v4-3-5-queue-metaexamples-fiddle-line97-eg1
    returncode: 0

2. metaexamples-fiddle-line99-eg2

    manifest_verdict: PATCH_ACCEPTED
    patch_certificate_id: sorrydb-v4-3-5-queue-metaexamples-fiddle-line99-eg2
    returncode: 0

## Bounded claim

The streaming-enabled queue runner works under real Lean contact for the two known exact-source candidates. It produced visible progress, a partial summary, two accepted manifests, two emitted certificates, and restored the source file.

## Does not claim

- general proof repair
- arbitrary SorryDB automation
- declaration retrieval success
- multi-file patching
- upstream submission

## Importance

v4.3.6 proved the queue runner worked, but it was operator-silent during child replay. v4.3.7 added streaming and partial summaries. v4.3.8 proves that the visibility fix survives real Lean replay, not only fake unit tests.

## Next frontier

Run a larger 10–20 candidate queue or build a miner that generates exact-source queue candidates from SorryDB rows.
