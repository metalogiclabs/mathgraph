import Lean

/-! Protected negative: the original unguarded instance is not a theorem. -/
example : (1 + 1 > 1 + 1) := by decide
