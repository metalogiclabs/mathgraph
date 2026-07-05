# SorryDB v4.4.20 — Human Review Boundary and Fresh-Source Pilot Plan

## Immediate path

Manual outbound review.

The v4.4.19 outbound message package is ready, but human approval is required before any external contact.

## Follow-up technical path

Tiny fresh-source replay pilot.

Constraints:

- at most five candidate targets
- exact-source match or named adapter required
- no broad mining
- no heavy lake build without explicit approval
- terminal states must be accepted, failed, or named obstruction

## Current outbound subject

Two exact-source Lean repairs for MetaExamples/Fiddle.lean with replay evidence

## Current outbound message snapshot

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


## Bounded claim

- v4.4.20 records that the immediate next step after v4.4.19 is manual human review of the outbound upstream message.
- v4.4.20 selects a tiny fresh-source replay pilot as the next technical follow-up after the human-review boundary.
- the pilot is constrained to at most five targets and exact-source match or named adapter outcomes.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run broad clone/build jobs on low disk
