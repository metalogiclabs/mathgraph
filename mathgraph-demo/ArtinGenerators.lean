import Mathlib.GroupTheory.Subgroup.Centralizer

open Subgroup

theorem Artin_exercise_2_2_9 {G : Type*} [Group G] {a b : G}
  (h : a * b = b * a) :
  ∀ x y : closure {x | x = a ∨ x = b}, x * y = y * x := by
  letI : CommGroup (closure {x : G | x = a ∨ x = b}) :=
    closureCommGroupOfComm (by
      intro x hx y hy
      rcases hx with rfl | rfl <;> rcases hy with rfl | rfl
      · rfl
      · exact h
      · exact h.symm
      · rfl)
  intro x y
  exact mul_comm x y
