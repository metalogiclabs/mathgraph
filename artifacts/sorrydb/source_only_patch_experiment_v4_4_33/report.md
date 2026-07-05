# SorryDB v4.4.33 — Source-Only Patch Experiment

## Result

- repo: teorth/equational_theories
- commit: b1cc1756202d7f44e07bd4069b5df16901a36938
- target path: equational_theories/Definability/Law43.lean
- target sorry line: 15
- definability context windows: 7
- patch candidate count: 5
- selected patch: patch-001-exact-constructor-four-fields
- selected patch score: 48
- build attempted: false
- replay attempted: false

## Selected patch

- patch id: patch-001-exact-constructor-four-fields
- score: 48
- reasons: removes active sorry, uses exact, uses hSymm, uses arity hypotheses, uses swap witness, rough delimiter balance ok
- rationale: try direct constructor witness: swapped variable map plus arity hypotheses plus symmetry equation

```lean
exact ⟨fun x ↦ Lf (Equiv.swap 0 1 x), hL2args, hR2args, hSymm⟩
```

## Patched local window

```lean
11:     (hL2args : ∀ e ∈ L.lhs.elems.1, e ∈ [0,1] := by decide +kernel)
12:     (hR2args : ∀ e ∈ L.rhs.elems.1, e ∈ [0,1] := by decide +kernel)
13:     (hSymm : L.lhs ⬝ (fun x ↦ Lf $ Equiv.swap 0 1 x) = L.rhs := by rfl)
14:     : Law43.TermDefinableFrom L := by
15:   exact ⟨fun x ↦ Lf (Equiv.swap 0 1 x), hL2args, hR2args, hSymm⟩
16: 
17: /-- The commutative law 43 `x ◇ y = y ◇ x` is TermDefinable from 40 `x ◇ x = y ◇ y`. -/
18: theorem Equation43_termDefinableFrom_Equation40 : Law43.TermDefinableFrom Law40 :=
19:   Equation43_termDefinableFrom_swapped_args
20: 
```

## TermDefinableFrom context

```lean
120: -/
121: def TermDefinableOnMagma (L : Law.MagmaLaw β) (M : Magma G) : Prop :=
122:   --If there exists a magma M',
123:   ∃ M' : Magma G,
124:     -- satisfying the law L,
125:     @satisfies _ G M' L ∧
126:     -- with a graph equal to some formula in M.
127:     (@Set.TermDefinable _ ∅ MagmaLanguage M.FOStructure _ M'.FinArityOp)
128: 
129: /-- A MagmaLaw L is term-definable from another law L' if L is DefinableOn every magma satisfying L'. -/
130: def TermDefinableFrom (L L' : Law.MagmaLaw β) : Prop :=
131:   ∀ {G : Type} (M : Magma G), satisfies G L' → TermDefinableOnMagma L M
132: 
133: /-- A MagmaLaw L is structural on a given Magma ⟨M,◇⟩ there is a Magma ⟨M,□⟩ satisfying L, so that ◇
134: and □ are first-order definable in terms of each other. This doesn't necessarily imply that □ is
135: uniquely determined, but it means that □ can hold all of the information of the magma. -/
136: def StructuralOnMagma (L : Law.MagmaLaw β) (M : Magma G) : Prop :=
137:   --If there exists a magma M',
138:   ∃ M' : Magma G,
139:     -- satisfying the law L,
140:     @satisfies _ G M' L ∧
```

## Boundary

No Lean build, Lean replay, upstream modification, or maintainer contact was performed.

## Next frontier

Run bounded Lean replay for the selected patch only, with strict timeout and no upstream contact.
