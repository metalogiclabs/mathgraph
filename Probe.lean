import PropertyKindCalculus.Uncertainty.Sensitivity
open TorchLean
open PropertyKindCalculus.Paradigm
open PropertyKindCalculus.Uncertainty.Sensitivity

def model (dead : String) : ScalarModel := fun xs => ⟨do
  let x ← match xs with
    | a :: _ => a.run
    | [] => throw "missing input"
  if dead == "sqrt" then
    let _ ← TapeM.sqrt (s := Shape.scalar) x
    pure ()
  else if dead == "log" then
    let _ ← TapeM.log (s := Shape.scalar) x
    pure ()
  else if dead == "exp" then
    let _ ← TapeM.exp (s := Shape.scalar) x
    pure ()
  else pure ()
  pure x⟩

def main : IO Unit := do
  for x in ([0.0, 1.0, 1000.0] : List Float) do
    for op in ["none", "sqrt", "log", "exp"] do
      match gradient (model op) [x] with
      | .error e => IO.println s!"x={x} op={op} ERROR {e}"
      | .ok gs => IO.println s!"x={x} op={op} gradients={gs}"
    match gradient (model "none") [x] with
    | .ok [g] => unless g == 1.0 do throw (IO.userError "baseline failed")
    | _ => throw (IO.userError "baseline failed")
