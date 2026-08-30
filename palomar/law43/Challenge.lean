import MathGraphPalomarLaw43

/-!
# Swapped-arguments laws define a commutative derived operation

The trusted statement surface is self-contained. A binary magma law is represented
by a pair of two-variable terms `lhs` and `rhs`. If `rhs` is exactly the variable-
swap of `lhs`, and the magma operation satisfies that law for all inputs, then the
operation obtained by evaluating `lhs` is term-defined and commutative.
-/

namespace MathGraphPalomar

/--
A swapped-arguments magma identity canonically yields a commutative derived binary
operation, explicitly defined by the left-hand term.
-/
theorem main_result {α : Type} (mul : α → α → α) (lhs rhs : Term)
    (hSwap : rhs = lhs.swap)
    (hSat : ∀ x y, lhs.eval mul x y = rhs.eval mul x y) :
    ∃ derived : α → α → α,
      (∀ x y, derived x y = lhs.eval mul x y) ∧
      (∀ x y, derived x y = derived y x) := by
  sorry

end MathGraphPalomar
