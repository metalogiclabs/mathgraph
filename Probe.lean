import PropertyKindCalculus.Uncertainty.Sensitivity
open TorchLean
open PropertyKindCalculus.Paradigm
open PropertyKindCalculus.Uncertainty.Sensitivity

def recordDead (op : String) (x : Nat) : TapeM Float Unit := do
  if op == "none" then pure ()
  else
    let _ ← match op with
      | "sqrt" => TapeM.sqrt (s := Shape.scalar) x
      | "log" => TapeM.log (s := Shape.scalar) x
      | "exp" => TapeM.exp (s := Shape.scalar) x
      | "abs" => TapeM.abs (s := Shape.scalar) x
      | "add" => TapeM.add (s := Shape.scalar) x x
      | "sub" => TapeM.sub (s := Shape.scalar) x x
      | "mul" => TapeM.mul (s := Shape.scalar) x x
      | "div" => TapeM.div (s := Shape.scalar) x x
      | "min" => TapeM.min (s := Shape.scalar) x x
      | "max" => TapeM.max (s := Shape.scalar) x x
      | _ => throw "unknown op"
    pure ()

def model (op : String) (active : Bool) : ScalarModel := fun xs => ⟨do
  let x ← match xs with
    | a :: _ => a.run
    | [] => throw "missing input"
  let out ← if active then TapeM.mul (s := Shape.scalar) x x else pure x
  recordDead op x
  pure out⟩

def main : IO Unit := do
  for x in ([-1000.0, -1.0, -0.0, 0.0, 1.0, 1000.0] : List Float) do
    for active in [false,true] do
      for op in ["none","sqrt","log","exp","abs","add","sub","mul","div","min","max"] do
        let expected := if active then 2*x else 1.0
        match gradient (model op active) [x] with
        | .error e => IO.println s!"CASE x={x} active={active} op={op} ERROR {e}"
        | .ok [g] => IO.println s!"CASE x={x} active={active} op={op} gradient={g} expected={expected} pass={g == expected}"
        | .ok _ => throw (IO.userError "unexpected gradient arity")
