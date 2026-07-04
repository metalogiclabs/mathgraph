# SorryDB v4.3.2 Patch Certificate Schema

v4.3.2 promotes the accepted v4.3.1 patch replays from prose ledger entries into reusable JSON patch certificates.

Each certificate records:

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

The trust boundary is exact-source-snippet plus Lean replay.

This is intentionally narrower than general proof repair. A patch certificate says:

Given an exact source snippet in a baseline-passing Lean project, replacing that snippet with the patch snippet made Lean accept the file, and the original source was restored afterward.

Included certificates:

1. sorrydb-v4-3-2-metaexamples-fiddle-line97-eg1
2. sorrydb-v4-3-2-metaexamples-fiddle-line99-eg2

Both have final_verdict PATCH_ACCEPTED.

Next frontier: make the runner emit this certificate format automatically from manifest output.
