import Mathlib.GroupTheory.Subgroup.Centralizer

open Subgroup

theorem Artin_exercise_2_2_9 {G : Type*} [CommGroup G] {a b : G}
  (h : a * b = b * a) :
  ∀ x y : closure {x | x = a ∨ x = b}, x * y = y * x := by
  intro x y
  exact mul_comm x y
