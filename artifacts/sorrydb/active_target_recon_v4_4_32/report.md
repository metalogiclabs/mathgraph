# SorryDB v4.4.32 — Active Target Recon

## Result

- repo: teorth/equational_theories
- commit: b1cc1756202d7f44e07bd4069b5df16901a36938
- target path: equational_theories/Definability/Law43.lean
- target exists: True
- Lean toolchain: leanprover/lean4:v4.29.1
- Lean4 likely: True
- active sorry count: 1
- replay risk: MEDIUM_HIGH_BUT_REAL_LEAN4_TARGET
- build attempted: false
- replay attempted: false
- patch attempted: false
- decision: READY_FOR_BOUNDED_SOURCE_ONLY_PATCH_EXPERIMENT_NO_UPSTREAM_CONTACT

## Risk reasons

- Lean4/lake repo detected
- target file exists at selected commit
- single active sorry remains in target file
- target depends on local equational_theories imports
- definability theorem likely depends on project-specific infrastructure
- uses decide +kernel syntax nearby
- rfl witness nearby

## Imports

import Batteries.Data.List.Basic
import equational_theories.Definability.Basic
import equational_theories.Equations.All

## First active sorry window

10: theorem Equation43_termDefinableFrom_swapped_args {L : NatMagmaLaw}
11:     (hL2args : ∀ e ∈ L.lhs.elems.1, e ∈ [0,1] := by decide +kernel)
12:     (hR2args : ∀ e ∈ L.rhs.elems.1, e ∈ [0,1] := by decide +kernel)
13:     (hSymm : L.lhs ⬝ (fun x ↦ Lf $ Equiv.swap 0 1 x) = L.rhs := by rfl)
14:     : Law43.TermDefinableFrom L := by
15:   sorry
16: 
17: /-- The commutative law 43 `x ◇ y = y ◇ x` is TermDefinable from 40 `x ◇ x = y ◇ y`. -/
18: theorem Equation43_termDefinableFrom_Equation40 : Law43.TermDefinableFrom Law40 :=
19:   Equation43_termDefinableFrom_swapped_args
20: 

## Boundary

Repo was cloned only into `.tmp_sorrydb_v4_4_32_active_target_recon`. No Lean build, Lean replay, patch, upstream modification, or maintainer contact was performed.

## Next frontier

Run a bounded source-only patch experiment on the exact target file, then replay only if the patch is syntactically plausible.
