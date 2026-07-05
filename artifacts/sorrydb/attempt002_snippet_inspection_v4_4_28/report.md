# SorryDB v4.4.28 — Attempt 002 Snippet Inspection

## Result

- inspected candidate count: 5
- fetch ok count: 5
- candidate with sorry count: 5
- selected candidate: attempt002-candidate-007
- selected repo: EdAyers/lean-subtask
- selected path: src/examples/vector.lean
- replay attempted: false

## Selected candidate

- candidate id: attempt002-candidate-007
- repo: EdAyers/lean-subtask
- path: src/examples/vector.lean
- url: https://github.com/EdAyers/lean-subtask/blob/04ac5a6c3bc3bfd190af4d6dcce444ddc8914e4b/src/examples/vector.lean
- sorry count: 1
- line count: 71
- replay selection score: 19
- reasons: single sorry, small file, example context

## First sorry window

63:     ⟪ A† ( u + v ) + w , x ⟫ = ⟪ A† u + w + A† v , x ⟫
64: := by equate
65: 
66: /- Can it find a better solution to the problem if we add in the proof that A† is linear? -/
67: @[equate] lemma adj_linear_2 (il : is_linear A) : A†(x + y) = A†x + A†y := sorry
68: 
69: example (il : is_linear A) :
70:     ⟪ A† ( u + v ) + w , x ⟫ = ⟪ A† u + w + A† v , x ⟫
71: := by equate

## Boundary

No clone, Lean replay, upstream modification, or maintainer contact was performed.

## Next frontier

Clone only the selected repo into a bounded temp directory and run source/Lean-version reconnaissance before replay.
