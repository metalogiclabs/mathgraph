namespace MathGraphPalomar

/-- Binary magma terms in two variables. -/
inductive Term where
  | x : Term
  | y : Term
  | op : Term → Term → Term
  deriving Repr, DecidableEq

namespace Term

/-- Evaluate a two-variable magma term in a binary operation. -/
def eval {α : Type} (mul : α → α → α) : Term → α → α → α
  | x, a, _ => a
  | y, _, b => b
  | op l r, a, b => mul (eval mul l a b) (eval mul r a b)

/-- Swap the two variables everywhere in a term. -/
def swap : Term → Term
  | x => y
  | y => x
  | op l r => op (swap l) (swap r)

end Term

end MathGraphPalomar
