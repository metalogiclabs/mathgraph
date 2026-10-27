import Lean

/-! This source MUST fail to compile; it is a protected negative control. -/

example : ((1 / 2 : Rat) ≤ (0 : Rat)) := by decide
