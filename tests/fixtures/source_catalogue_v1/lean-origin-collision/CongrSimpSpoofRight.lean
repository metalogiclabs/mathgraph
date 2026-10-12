module

public import HCongrDefs

@[expose] public section

namespace Origin

run_meta
  let target := Lean.mkConst ``Origin.congrTarget
  let some congr ← Lean.Meta.mkCongrSimp? target
    | throwError "failed to construct congr_simp theorem"
  Lean.addDecl <| ← Lean.mkThmOrUnsafeDef {
    name := `Origin.congrTarget.congr_simp
    levelParams := []
    type := congr.type
    value := congr.proof
  }

theorem forceSpoofCongrSimpRight : congrTarget 1 2 3 = 6 := by decide

end Origin
