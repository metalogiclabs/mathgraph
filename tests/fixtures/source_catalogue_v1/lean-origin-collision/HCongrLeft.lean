module

public import HCongrDefs

@[expose] public section

namespace Origin

run_meta
  let some _ ← Lean.Meta.mkHCongrWithArityForConst? ``Origin.congrTarget [] 3
    | throwError "failed to generate sibling hcongr theorem"

theorem forceHCongrLeft : congrTarget 1 2 3 = 6 := by decide

end Origin
