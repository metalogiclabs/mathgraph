module

public import HCongrDefs

@[expose] public section

namespace Origin

run_meta
  let name := Lean.Name.str ``Origin.congrTarget Lean.Meta.congrSimpSuffix
  Lean.addDecl <| ← Lean.mkThmOrUnsafeDef {
    name
    levelParams := []
    type := Lean.mkConst ``True
    value := Lean.mkConst ``True.intro
  }
  Lean.modifyEnv fun env => Lean.Meta.congrKindsExt.insert env name #[]

theorem forceForgedCongrSimpLeft : congrTarget 1 2 3 = 6 := by decide

end Origin
