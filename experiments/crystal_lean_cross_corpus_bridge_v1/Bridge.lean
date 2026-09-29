import Mathlib.NumberTheory.FLT.Basic

/-!
Bounded semantic bridge between the public Anthropic FLT theorem surface and
the Mathlib/Isomorphic-AI fixed-exponent FLT surface.

This proves statement transport only. It does not import the Anthropic proof.
-/

def AnthropicFLTFor (n : ℕ) : Prop :=
  ∀ a b c : ℕ, 0 < a → 0 < b → 0 < c → a ^ n + b ^ n ≠ c ^ n

abbrev IsomorphicHoldsAt (n : ℕ) : Prop := FermatLastTheoremFor n

theorem anthropicFLTFor_iff_mathlib (n : ℕ) :
    AnthropicFLTFor n ↔ FermatLastTheoremFor n := by
  constructor
  · intro h a b c ha hb hc
    exact h a b c (Nat.pos_of_ne_zero ha) (Nat.pos_of_ne_zero hb) (Nat.pos_of_ne_zero hc)
  · intro h a b c ha hb hc
    exact h a b c (Nat.ne_of_gt ha) (Nat.ne_of_gt hb) (Nat.ne_of_gt hc)

theorem anthropicFLTFor_iff_isomorphicHoldsAt (n : ℕ) :
    AnthropicFLTFor n ↔ IsomorphicHoldsAt n :=
  anthropicFLTFor_iff_mathlib n

def AnthropicFLT : Prop :=
  ∀ n : ℕ, 3 ≤ n → AnthropicFLTFor n

theorem anthropicFLT_iff_mathlibFLT :
    AnthropicFLT ↔ FermatLastTheorem := by
  constructor
  · intro h n hn
    exact (anthropicFLTFor_iff_mathlib n).mp (h n hn)
  · intro h n hn
    exact (anthropicFLTFor_iff_mathlib n).mpr (h n hn)

theorem reuse_anthropic_as_isomorphic {n : ℕ}
    (h : AnthropicFLTFor n) : IsomorphicHoldsAt n :=
  (anthropicFLTFor_iff_isomorphicHoldsAt n).mp h

theorem reuse_isomorphic_as_anthropic {n : ℕ}
    (h : IsomorphicHoldsAt n) : AnthropicFLTFor n :=
  (anthropicFLTFor_iff_isomorphicHoldsAt n).mpr h
