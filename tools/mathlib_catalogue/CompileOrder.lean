import Lean

/- Transient build planning from verified source headers, parsed by Lean.
   These dependencies never become published relations or proof authority.
   No cached selected environment, Lake script, or declaration body is loaded. -/
open Lean

partial def visit (sources : SearchPath) (selected : Array Name) (name : Name)
    (active seen : NameSet) (order : Array String) : IO (NameSet × Array String) := do
  if active.contains name then throw <| IO.userError s!"cyclic source imports at {name}"
  if seen.contains name then return (seen, order)
  let some path ← sources.findModuleWithExt "lean" name
    | throw <| IO.userError s!"missing verified import source {name}"
  let (imports, _, messages) ← Elab.parseImports (← IO.FS.readFile path) path.toString
  if messages.hasErrors then throw <| IO.userError s!"invalid source import header {path}"
  let active := active.insert name
  let mut seen := seen
  let mut order := order
  for imp in imports do
    let result ← visit sources selected imp.module active seen order
    seen := result.1
    order := result.2
  if selected.contains name then order := order.push (name.toString (escape := true))
  return (seen.insert name, order)

unsafe def main (args : List String) : IO Unit := do
  let output :: modules := args | throw <| IO.userError "expected OUTPUT MODULE..."
  unless !modules.isEmpty && modules.eraseDups == modules do
    throw <| IO.userError "unique selected modules required"
  let names := modules.toArray.map String.toName
  let some roots ← IO.getEnv "LEAN_SRC_PATH"
    | throw <| IO.userError "explicit verified source search roots required"
  unless !roots.isEmpty do throw <| IO.userError "empty verified source search roots"
  let sources ← getSrcSearchPath
  let mut seen : NameSet := {}
  let mut order := #[]
  for name in names do
    let result ← visit sources names name {} seen order
    seen := result.1
    order := result.2
  unless order.size == names.size do throw <| IO.userError "incomplete compilation order"
  IO.FS.writeFile output (Json.mkObj [("modules", toJson order)]).compress
