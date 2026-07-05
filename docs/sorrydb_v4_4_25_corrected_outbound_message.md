# SorryDB v4.4.25 — Corrected Outbound Message

v4.4.25 corrects the human-facing outbound message before any upstream contact.

## Why

The v4.4.19 outbound message duplicated the Patch 1 summary in the Patch 2 slot.

## Bounded claim

- v4.4.25 corrects the human-facing outbound message by deriving both patch descriptions from the patch bundle.
- v4.4.25 detects and rejects duplicated replacement snippets.
- no upstream message is sent and no Lean replay is executed.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- upstream acceptance
- automated external contact
- that any fresh target verifies
- permission to run heavy lake builds on low disk

## Next frontier

manual review of `artifacts/sorrydb/corrected_outbound_message_v4_4_25/corrected_outbound_message.md`, then decide whether to send upstream.
