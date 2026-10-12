module

public import OriginDefs

@[expose] public section

namespace Origin

run_meta
  discard <| Lean.Meta.getEqnsFor? ``Origin.duplicatedEquation

theorem forceInBasic (n : Nat) (h : duplicatedEquation n) : n = n := h.1

end Origin
