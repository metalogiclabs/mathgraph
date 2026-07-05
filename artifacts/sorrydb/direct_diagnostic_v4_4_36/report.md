# SorryDB v4.4.36 — Direct Diagnostic

## Result

- repo: teorth/equational_theories
- target path: equational_theories/Definability/Law43.lean
- selected patch: patch-001-exact-constructor-four-fields
- cache get ok: True
- target replay ok: False
- target replay returncode: 1
- obstruction class: LOCAL_PROJECT_OLEAN_NOT_BUILT
- proof patch dead: false
- upstream contact performed: false

## Obstruction reasons

- target replay failed because local project library prefix was not built into .lake/build/lib/lean
- Lean search path lacks equational_theories.olean
- dependency cache completed, but project-local olean was still missing

## Interpretation

The patch has not reached a clean proof/type judgment. `lake exe cache get` succeeded, but `lake env lean equational_theories/Definability/Law43.lean` failed because the local project module prefix `equational_theories` was not built into the local search path as an `.olean`.

## Next action

Run a targeted Lake build/replay path that builds the local project module first, then replay the same patch.

## Boundary

No upstream modification or maintainer contact was performed.
