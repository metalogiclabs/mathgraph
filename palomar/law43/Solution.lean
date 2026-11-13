import MathGraphPalomarLaw43

namespace MathGraphPalomar

private theorem eval_swap {α : Type} (mul : α → α → α) :
    ∀ (t : Term) (x y : α), t.swap.eval mul x y = t.eval mul y x := by
  intro t
  induction t with
  | x => intro x y; rfl
  | y => intro x y; rfl
  | op l r ihl ihr =>
      intro x y
      simp [Term.swap, Term.eval, ihl, ihr]

/-- Proved form of the advertised swapped-arguments term-definability result. -/
theorem main_result {α : Type} (mul : α → α → α) (lhs rhs : Term)
    (hSwap : rhs = lhs.swap)
    (hSat : ∀ x y, lhs.eval mul x y = rhs.eval mul x y) :
    ∃ derived : α → α → α,
      (∀ x y, derived x y = lhs.eval mul x y) ∧
      (∀ x y, derived x y = derived y x) := by
  refine ⟨fun x y => lhs.eval mul x y, ?_, ?_⟩
  · intro x y
    rfl
  · intro x y
    have h := hSat x y
    rw [hSwap, eval_swap] at h
    exact h

end MathGraphPalomar
