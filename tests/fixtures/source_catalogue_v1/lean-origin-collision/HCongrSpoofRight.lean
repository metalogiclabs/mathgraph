module

public import HCongrDefs

@[expose] public section

namespace Origin

run_meta
  let target := Lean.mkConst ``Origin.congrTarget
  let congr ← Lean.Meta.mkHCongrWithArity target 3
  Lean.addDecl <| ← Lean.mkThmOrUnsafeDef {
    name := `Origin.congrTarget.hcongr_3
    levelParams := []
    type := congr.type
    value := congr.proof
  }

theorem forceSpoofHCongrRight : congrTarget 1 2 3 = 6 := by decide

end Origin
