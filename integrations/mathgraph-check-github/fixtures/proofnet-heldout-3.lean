import Mathlib

open Function Fintype Subgroup Ideal Polynomial Submodule Zsqrtd
open scoped BigOperators



/-Informal Statement

Prove that a group of even order contains an element of order $2 .$
-/

theorem Artin_exercise_2_11_3 {G : Type*} [Group G] [Fintype G]
  (hG : Even (card G)) : ∃ x : G, orderOf x = 2 := by
  sorry
