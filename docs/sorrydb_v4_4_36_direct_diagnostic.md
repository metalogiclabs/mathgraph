# SorryDB v4.4.36 — Direct Diagnostic

v4.4.36 records the direct dependency-aware diagnostic run.

## Bounded claim

- v4.4.36 records the direct dependency-aware diagnostic run.
- it identifies the failure as local project olean/module setup, not proof rejection.
- it keeps the selected patch alive until a target build/replay reaches proof checking.

## Does not claim

- patch acceptance
- proof rejection
- upstream acceptance
- automated external contact
- full repository build success

## Next frontier

Run a targeted Lake build/replay path that builds the local project module first, then replay the same patch.
