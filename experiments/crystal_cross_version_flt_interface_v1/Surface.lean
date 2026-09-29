import Mathlib.NumberTheory.FLT.Basic

theorem crystal_fixedExponent_surface (n : ℕ) :
    FermatLastTheoremFor n ↔
      ∀ a b c : ℕ, a ≠ 0 → b ≠ 0 → c ≠ 0 →
        a ^ n + b ^ n ≠ c ^ n := by
  rfl

theorem crystal_global_surface :
    FermatLastTheorem ↔
      ∀ n : ℕ, n ≥ 3,
        ∀ a b c : ℕ, a ≠ 0 → b ≠ 0 → c ≠ 0 →
          a ^ n + b ^ n ≠ c ^ n := by
  rfl
