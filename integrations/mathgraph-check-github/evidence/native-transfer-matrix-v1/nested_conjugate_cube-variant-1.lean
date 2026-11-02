import Mathlib

theorem nested_conjugate_cube {G : Type*} [Group G] (a b c : G) : (a * b * c * b⁻¹ * a⁻¹) ^ 3 = a * b * c ^ 3 * b⁻¹ * a⁻¹ := by simp only [pow_succ, pow_zero, mul_one]; group
