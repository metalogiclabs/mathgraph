import Mathlib

theorem already_valid_cancellation {G : Type*} [Group G] (a b : G) : a * b * b⁻¹ = a := by group
