module

public import Lean

@[expose] public section

namespace Origin

def duplicatedEquation (n : Nat) : Prop := n = n ∧ True

theorem forceInDefs (n : Nat) (h : duplicatedEquation n) : n = n := h.1

end Origin
