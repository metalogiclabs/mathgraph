import Mathlib

namespace CrystalCrossProverCounterexample

theorem not_amgm3 : ¬ (∀ x y : ℝ, x ^ 2 + y ^ 2 ≥ 3 * x * y) := by
  intro h
  have h11 := h 1 1
  norm_num at h11

end CrystalCrossProverCounterexample
