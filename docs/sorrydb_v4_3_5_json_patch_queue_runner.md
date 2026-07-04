# SorryDB v4.3.5 JSON Patch Queue Runner

v4.3.5 adds a small JSON patch queue runner.

Input:

    artifacts/sorrydb/patch_queues/sorrydb_v4_3_5_two_known_accepted_patches.json

Each candidate records:

- candidate_id
- repo_root
- file_path
- source_snippet
- patch_snippet
- optional project metadata
- optional certificate metadata
- optional restore check

Default safety:

    SORRYDB_V435_ALLOW_RUN=0

When disabled, the runner validates the queue and emits:

    QUEUE_RUN_DISABLED

When enabled, the runner calls the v4.3.0 controlled patch replay runner once per candidate. The underlying replay runner performs baseline check, exact source replacement, Lean replay, source restoration, and automatic certificate emission.

Bounded claim:

v4.3.5 adds queue orchestration around exact-source patch candidates.

Does not claim:

- general proof repair
- arbitrary SorryDB automation
- declaration retrieval success
- multi-file patching
- upstream submission

Next frontier:

Run the queue with SORRYDB_V435_ALLOW_RUN=1 and require two PATCH_ACCEPTED manifests plus two emitted certificates.
