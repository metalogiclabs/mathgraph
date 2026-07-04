# SorryDB v4.4.4 Controlled Source Input Ledger

## Purpose

v4.4.4 makes source availability explicit for the four v4.4.3 `BACKFILL_BLOCKED_SOURCE_MISSING` rows. It records whether each row has a controlled in-repository source file, only an unstable external checkout path, snippet-only evidence, or insufficient source evidence.

The ledger prevents hidden dependence on `/tmp` and user-local source checkouts. A source file is `SOURCE_CHECKOUT_AVAILABLE` only when it exists inside an explicitly controlled source directory. Merely existing at a historical absolute path is not enough.

## Controlled snippet evidence

For every row with a source snippet, the ledger emits a small JSON record under:

`artifacts/sorrydb/source_inputs_v4_4_4/source_snippets/`

Each record contains the exact source and patch snippets, SHA256 hashes, file and certificate identity, and source-input status. These snippets and hashes are controlled inputs, but snippet-only or unstable-path rows are not replay-ready and are not accepted claims.

## Current result

All four rows retain exact snippet evidence, but their only recoverable checkout root is a historical `/tmp` path. They are classified `SOURCE_CHECKOUT_PATH_UNSTABLE`. No full external source checkout is copied into Git.

## Boundary

v4.4.4 performs JSON, file, text, and source-input accounting only. It does not run Lean and does not prove or replay patches.

Bounded claim: it classifies missing-source backfill rows into controlled source-input statuses and emits snippet/hash evidence.

It does not claim:

- new proof discovery;
- Lean replay success;
- source hydration;
- general SorryDB mining;
- arbitrary proof repair; or
- upstream submission.

## Next frontier

Choose among a v4.4.5 source hydration plan, a controlled small source fixture package, or manual source checkout registration based on the recorded statuses.
