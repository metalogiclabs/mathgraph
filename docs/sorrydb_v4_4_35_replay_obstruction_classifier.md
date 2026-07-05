# SorryDB v4.4.35 — Replay Obstruction Classifier

v4.4.35 classifies the v4.4.34 replay failure without rerunning Lean.

## Bounded claim

- v4.4.35 classifies the v4.4.34 replay failure without rerunning Lean.
- it separates dependency/bootstrap obstruction from proof/type obstruction.
- it prevents incorrectly marking the selected patch dead from setup-only evidence.

## Does not claim

- new Lean replay
- patch acceptance
- proof rejection
- full repository build
- upstream acceptance
- automated external contact

## Next frontier

v4.4.36 run a dependency-aware cache/build diagnostic, then replay the same patch only if the environment is ready.
