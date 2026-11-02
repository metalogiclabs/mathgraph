import Mathlib

theorem conjugate_power_2 {G : Type*} [Group G] (a b : G) : (a * b * a⁻¹) ^ 2 = a * b ^ 2 * a⁻¹ := by group
