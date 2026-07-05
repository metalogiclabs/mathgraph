## Summary

This corrects the v4.4.19 outbound upstream message package.

The previous outbound message duplicated the Patch 1 summary in the Patch 2 slot. v4.4.25 regenerates the outbound text directly from the v4.4.17 patch bundle replacement snippets and records the correction before any manual upstream contact.

## Evidence

- target repo: `siddhartha-gadgil/MetaExamples`
- target commit: `edbb75e784db19846a1c19841e182b797afc18bb`
- target file: `MetaExamples/Fiddle.lean`
- exact-source patch candidates: 2
- accepted replay certificates: 4
- deduplicated repair classes: 2

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
