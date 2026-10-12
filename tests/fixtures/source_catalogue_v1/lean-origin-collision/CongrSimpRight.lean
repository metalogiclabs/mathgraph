module

public import HCongrDefs

@[expose] public section

namespace Origin

run_meta
  let some _ ← Lean.Meta.mkCongrSimpForConst? ``Origin.congrTarget []
    | throwError "failed to generate sibling congr_simp theorem"

theorem forceCongrSimpRight : congrTarget 1 2 3 = 6 := by decide

end Origin
