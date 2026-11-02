import Mathlib

theorem conjugate_power_3 {G : Type*} [Group G] (a b : G) : (a * b * a⁻¹) ^ 3 = a * b ^ 3 * a⁻¹ := by simp only [pow_succ, pow_zero, mul_one]; group
