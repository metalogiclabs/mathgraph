# SorryDB v4.3.3 Automatic Certificate Emitter

v4.3.3 updates the controlled patch replay runner so accepted patch replays emit reusable patch certificates automatically.

When a run ends with:

    verdict=PATCH_ACCEPTED

the runner now writes:

    patch_certificates/<certificate_id>.json

inside the run artifact directory.

The emitted certificate follows the v4.3.2 schema:

- certificate_id
- certificate_version
- status
- project
- project_commit
- file_path
- source_snippet
- patch_snippet
- baseline_command
- patch_command
- baseline_verdict
- patch_apply_verdict
- patch_verdict
- final_verdict
- lean_returncode
- restore_check
- trust_boundary
- bounded_claim
- does_not_claim

The manifest also records:

- patch_certificate_path
- patch_certificate_id

Bounded claim:

Accepted patch replays are now automatically promoted into certificate JSON artifacts.

Does not claim:

- general proof repair
- declaration retrieval success
- multi-file patching
- repository-wide sorry elimination
- upstream submission

Next frontier:

Run the emitter on the two known accepted local patches and compare emitted certificates against the hand-authored v4.3.2 certificates.
