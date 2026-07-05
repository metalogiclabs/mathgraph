# SorryDB v4.4.34 — Bounded Replay

## Result

- repo: teorth/equational_theories
- commit: b1cc1756202d7f44e07bd4069b5df16901a36938
- target path: equational_theories/Definability/Law43.lean
- selected patch: patch-001-exact-constructor-four-fields
- timeout seconds: 360
- clone attempted: True
- patch attempted: True
- build attempted: False
- replay attempted: True
- replay status: REJECTED_BY_LOCAL_REPLAY
- decision: REPLAY_REJECTED_OR_TIMED_OUT_NO_UPSTREAM_CONTACT

## Replay reasons

- import/module failure
- Lean reported error

## Patch

```lean
exact ⟨fun x ↦ Lf (Equiv.swap 0 1 x), hL2args, hR2args, hSymm⟩
```

## Diff

```diff
diff --git a/equational_theories/Definability/Law43.lean b/equational_theories/Definability/Law43.lean
index e4e401f..b79dcab 100644
--- a/equational_theories/Definability/Law43.lean
+++ b/equational_theories/Definability/Law43.lean
@@ -12,7 +12,7 @@ theorem Equation43_termDefinableFrom_swapped_args {L : NatMagmaLaw}
     (hR2args : ∀ e ∈ L.rhs.elems.1, e ∈ [0,1] := by decide +kernel)
     (hSymm : L.lhs ⬝ (fun x ↦ Lf $ Equiv.swap 0 1 x) = L.rhs := by rfl)
     : Law43.TermDefinableFrom L := by
-  sorry
+  exact ⟨fun x ↦ Lf (Equiv.swap 0 1 x), hL2args, hR2args, hSymm⟩
 
 /-- The commutative law 43 `x ◇ y = y ◇ x` is TermDefinable from 40 `x ◇ x = y ◇ y`. -/
 theorem Equation43_termDefinableFrom_Equation40 : Law43.TermDefinableFrom Law40 :=

```

## Replay stderr tail

```text
info: Version 4.2.3 of elan is available! Use `elan self update` to update.
info: downloading https://releases.lean-lang.org/lean4/v4.29.1/lean-4.29.1-darwin_aarch64.tar.zst
info: installing /Users/heath/.elan/toolchains/leanprover--lean4---v4.29.1
info: checkdecls: cloning https://github.com/PatrickMassot/checkdecls.git
info: checkdecls: checking out revision '3d425859e73fcfbef85b9638c2a91708ef4a22d4'
info: mathlib: cloning https://github.com/leanprover-community/mathlib4.git
info: mathlib: checking out revision '5e932f97dd25535344f80f9dd8da3aab83df0fe6'
info: plausible: cloning https://github.com/leanprover-community/plausible
info: plausible: checking out revision '83e90935a17ca19ebe4b7893c7f7066e266f50d3'
info: LeanSearchClient: cloning https://github.com/leanprover-community/LeanSearchClient
info: LeanSearchClient: checking out revision 'c5d5b8fe6e5158def25cd28eb94e4141ad97c843'
info: importGraph: cloning https://github.com/leanprover-community/import-graph
info: importGraph: checking out revision '48d5698bc464786347c1b0d859b18f938420f060'
info: proofwidgets: cloning https://github.com/leanprover-community/ProofWidgets4
info: proofwidgets: checking out revision '4dd0959c44d1af0462bd604d0f87c5781307d709'
info: aesop: cloning https://github.com/leanprover-community/aesop
info: aesop: checking out revision '7152850e7b216a0d409701617721b6e469d34bf6'
info: Qq: cloning https://github.com/leanprover-community/quote4
info: Qq: checking out revision '707efb56d0696634e9e965523a1bbe9ac6ce141d'
info: batteries: cloning https://github.com/leanprover-community/batteries
info: batteries: checking out revision '756e3321fd3b02a85ffda19fef789916223e578c'
info: Cli: cloning https://github.com/leanprover/lean4-cli
info: Cli: checking out revision '7802da01beb530bf051ab657443f9cd9bc3e1a29'

```

## Boundary

No upstream modification or maintainer contact was performed.
