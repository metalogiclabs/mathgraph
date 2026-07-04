# SorryDB v4.4.6 Controlled Source Hydration Ledger

## Purpose

v4.4.6 hydrates exactly one allowlisted source identity:

- repository: `https://github.com/siddhartha-gadgil/MetaExamples`
- commit: `edbb75e784db19846a1c19841e182b797afc18bb`

The checkout is stored under the ignored `.mathgraph_source_cache/` directory. The script refuses multiple repository identities and refuses any URL/commit pair outside its explicit allowlist.

After detached checkout, the ledger verifies the actual commit, expected file, file SHA256, exact source-snippet occurrence count, source-snippet SHA256, patch-snippet SHA256, and unique snippet line span for each v4.4.5 hydration row.

## Boundary

This step performs controlled source hydration only. It does not run Lean, Lake, builds, replay, dependency hydration, or proof checking. It does not modify the hydrated source after checkout, and the full external checkout is not committed.

Only the following small artifacts are checked in:

- hydration summary;
- per-row source verification ledger;
- hydrated file hashes and sizes; and
- verified snippet hashes, counts, and line spans.

Bounded claim: the pinned source checkout was hydrated and the expected source snippets were verified against checked-in hashes.

It does not claim:

- Lean replay success;
- dependency hydration;
- proof checking;
- new proof discovery;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

v4.4.7 should rerun missing-manifest backfill planning against this controlled hydrated source cache and emit a backfill queue only if the rows become safely replay-ready.
