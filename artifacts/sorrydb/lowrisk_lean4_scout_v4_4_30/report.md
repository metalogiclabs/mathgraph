# SorryDB v4.4.30 — Low-Risk Lean4 Scout

## Parked previous candidate

- repo: EdAyers/lean-subtask
- target path: src/examples/vector.lean
- reason: DO_NOT_REPLAY_YET_REQUIRES_LEAN3_ENV_AND_EQUATE_CONTEXT

## Result

- unique candidate count: 126
- inspected candidate count: 30
- Lean4-likely count: 15
- selected candidate: lowrisk-lean4-030
- selected repo: FormalizedFormalLogic/Foundation
- selected path: Foundation/FirstOrder/Arithmetic/PeanoMinus/Q.lean
- selected score: 42

## Selected candidate

- repo: FormalizedFormalLogic/Foundation
- path: Foundation/FirstOrder/Arithmetic/PeanoMinus/Q.lean
- url: https://github.com/FormalizedFormalLogic/Foundation/blob/a1733b5c3bc1d34b84d31f31313398f8e53ba300/Foundation/FirstOrder/Arithmetic/PeanoMinus/Q.lean
- score: 42
- reasons: lean4 likely, single sorry, medium file, simp visible, rfl visible, nat visible, omega visible
- sorry count: 1
- line count: 162

## First sorry window

51: 
52: @[simp] lemma coe_add (a b : ℕ) : ↑(a + b) = ((↑a + ↑b) : OmegaAddOne) := rfl
53: 
54: -- @[simp] lemma coe_mul (a b : ℕ) : ↑(a * b) = ((↑a * ↑b) : OmegaAddOne) := sorry
55: 
56: @[simp] lemma lt_coe_iff (n m : ℕ) : (n : OmegaAddOne) < (m : OmegaAddOne) ↔ n < m := by rfl
57: 

## Boundary

No clone, Lean build, Lean replay, upstream modification, or maintainer contact was performed.

## Next frontier

Clone only the selected low-risk Lean4 candidate into a bounded temp directory and run manifest/source reconnaissance before replay.
