import Mathlib

theorem conjugate_power_4 {G : Type*} [Group G] (a b : G) : (a * b * a⁻¹) ^ 4 = a * b ^ 4 * a⁻¹ := by simp only [pow_succ, pow_zero, mul_one]; group
