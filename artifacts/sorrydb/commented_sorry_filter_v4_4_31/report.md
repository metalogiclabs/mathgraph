# SorryDB v4.4.31 — Commented Sorry Filter

## Result

- previous selected candidate: lowrisk-lean4-030
- previous selected repo: FormalizedFormalLogic/Foundation
- previous selected path: Foundation/FirstOrder/Arithmetic/PeanoMinus/Q.lean
- previous selected status: PARKED_COMMENTED_SORRY_ONLY
- evaluated candidate count: 20
- active candidate count: 14
- parked comment-only count: 6
- selected candidate: lowrisk-lean4-029
- selected repo: teorth/equational_theories
- selected path: equational_theories/Definability/Law43.lean

## Selected active candidate

- candidate id: lowrisk-lean4-029
- repo: teorth/equational_theories
- path: equational_theories/Definability/Law43.lean
- url: https://github.com/teorth/equational_theories/blob/b1cc1756202d7f44e07bd4069b5df16901a36938/equational_theories/Definability/Law43.lean
- active replay score: 66
- active sorry count: 1
- total sorry count: 1
- reasons: lean4 likely, single sorry, small file, rfl visible, nat visible, has active sorry, single active sorry

## First active sorry window

12:     (hR2args : ∀ e ∈ L.rhs.elems.1, e ∈ [0,1] := by decide +kernel)
13:     (hSymm : L.lhs ⬝ (fun x ↦ Lf $ Equiv.swap 0 1 x) = L.rhs := by rfl)
14:     : Law43.TermDefinableFrom L := by
15:   sorry
16: 
17: /-- The commutative law 43 `x ◇ y = y ◇ x` is TermDefinable from 40 `x ◇ x = y ◇ y`. -/
18: theorem Equation43_termDefinableFrom_Equation40 : Law43.TermDefinableFrom Law40 :=

## Boundary

No clone, Lean build, Lean replay, upstream modification, or maintainer contact was performed.

## Next frontier

Clone only the selected active-sorry candidate into a bounded temp directory and run manifest/source reconnaissance before replay.
