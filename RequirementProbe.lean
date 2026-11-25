import PropertyKindCalculus.Requirements.Attributes
open Lean PropertyKindCalculus.Requirements

open Lean Elab Command in
elab "#inspect_requirement" id:str : command => do
  let env ← getEnv
  let key := id.getString
  logInfo m!"{key}: {(requirementStatus env key).label}"

#inspect_requirement "R15"

@[requirement "R15" proves "negative control: unrelated theorem"]
theorem unrelated : True := trivial

#inspect_requirement "R15"

@[requirement "R14" proves "negative control: data rather than theorem"]
def unrelatedData : Nat := 7

#inspect_requirement "R14"
