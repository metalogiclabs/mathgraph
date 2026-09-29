import Mathlib.NumberTheory.FLT.Basic

namespace CrystalAnthropicConsumer

def PositiveFLTFor (n : ℕ) : Prop :=
  ∀ a b c : ℕ, 0 < a → 0 < b → 0 < c → a ^ n + b ^ n ≠ c ^ n

theorem positiveFLTFor_iff_mathlib (n : ℕ) :
    PositiveFLTFor n ↔ FermatLastTheoremFor n := by
  constructor
  · intro h a b c ha hb hc
    exact h a b c (Nat.pos_of_ne_zero ha) (Nat.pos_of_ne_zero hb) (Nat.pos_of_ne_zero hc)
  · intro h a b c ha hb hc
    exact h a b c (Nat.ne_of_gt ha) (Nat.ne_of_gt hb) (Nat.ne_of_gt hc)

end CrystalAnthropicConsumer
