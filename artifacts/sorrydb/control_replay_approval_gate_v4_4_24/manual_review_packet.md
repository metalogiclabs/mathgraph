# SorryDB v4.4.24 — Control Replay Approval Gate

## Decision

Replay is parked.

Reason: v4.4.23 produced approval-gated replay candidates, but no explicit approval token was provided here.

## Approval token required

APPROVE_PINNED_CONTROL_REPLAY_V4_4_24

## Ready counts

- control ready count: 1
- exact-source ready count: 2
- obstruction count: 2
- replay attempted: false

## Current outbound message

Hi,

I found two small exact-source repairs for MetaExamples/Fiddle.lean at commit edbb75e784db19846a1c19841e182b797afc18bb.

They replace two local sorry blocks with Lean terms that replayed successfully in my pinned checkout after cache hydration.

Patch 1:
Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Patch 2:
Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Evidence summary:

- target repo: siddhartha-gadgil/MetaExamples
- pinned commit: edbb75e784db19846a1c19841e182b797afc18bb
- target file: MetaExamples/Fiddle.lean
- exact-source patch candidates: 2
- accepted replay certificates: 4
- deduplicated repair classes: 2
- reviewer checklist artifact: artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md
- patch evidence bundle artifact: artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json

Important boundary:

This is not a claim of upstream acceptance, general proof repair, or portability. It is an exact-source evidence bundle: apply only if the source snippets match exactly, then rerun Lean in your checkout.

Suggested replay:

1. checkout siddhartha-gadgil/MetaExamples at edbb75e784db19846a1c19841e182b797afc18bb
2. run the baseline Lean check on MetaExamples/Fiddle.lean
3. apply the two exact-source replacements
4. rerun Lean on MetaExamples/Fiddle.lean
5. accept only if your checkout verifies

Thanks.


## If approved later

Use `pinned_control_replay_commands_not_executed.json`.

## Bounded claim

- v4.4.24 records the replay approval gate after the v4.4.23 replay-or-obstruction queue.
- because no explicit approval token is present, v4.4.24 parks replay and returns to manual outbound review.
- it packages the pinned control replay command list but does not execute it.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that exact-source-ready local matches are fresh targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- permission to run heavy lake builds on low disk
