import Lean

/-! This source MUST fail to compile; it is a protected negative control. -/

example : ((1 : Int) ≤ (0 : Int)) := by decide
