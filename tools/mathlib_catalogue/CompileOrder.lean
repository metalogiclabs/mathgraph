import Lean

/- Read only cached environment import data. No Lake script, source-token edge
   inference, build, acquisition, or mathematical authority is involved. -/
open Lean

partial def visit (env : Environment) (selected : Array Name) (name : Name)
    (seen : Array Name) (order : Array String) : Except String (Array Name × Array String) := do
  if seen.contains name then return (seen, order)
  let some idx := env.getModuleIdx? name | throw s!"unknown module {name}"
  let mut seen := seen.push name
  let mut order := order
  for imp in env.header.moduleData[idx]!.imports do
    let result ← visit env selected imp.module seen order
    seen := result.1
    order := result.2
  if selected.contains name then order := order.push (name.toString (escape := true))
  return (seen, order)

unsafe def main (args : List String) : IO Unit := do
  let output :: modules := args | throw <| IO.userError "expected OUTPUT MODULE..."
  unless !modules.isEmpty && modules.eraseDups == modules do
    throw <| IO.userError "unique selected modules required"
  initSearchPath (← getBuildDir)
  let names := modules.toArray.map String.toName
  let env ← importModules (names.map fun name => {module := name}) {} (loadExts := false)
  let mut seen := #[]
  let mut order := #[]
  for name in names do
    let result ← IO.ofExcept (visit env names name seen order)
    seen := result.1
    order := result.2
  unless order.size == names.size do throw <| IO.userError "incomplete compilation order"
  IO.FS.writeFile output (Json.mkObj [("modules", toJson order)]).compress
