import PropertyKindCalculus.Uncertainty.Adequacy32
open PropertyKindCalculus.Uncertainty

-- The local flag observes only one operand and the positive perturbation of the rounded sum.
-- The independent contract observes both individual perturbations of the original operands.
def changed (a b : Float32) : Bool := a.toBits != b.toBits

def main : IO Unit := do
  let half : Float32 := Float32.ofBits 0x33800000
  let small : Float32 := Float32.ofBits 0x33000000
  let one : Float32 := 1
  let next : Float32 := Float32.ofBits 0x3f800001
  for (name,v,d) in [("evenTie",one,half),("oddTie",next,half),("belowHalf",one,small)] do
    IO.println s!"TIE {name} absorbed={Adequacy32.absorbed v d}"
  let a := Adequacy32.input 2.0 small
  let b := Adequacy32.input 1.0 0.5
  let c := a + b
  let lostA := !changed (a.value+b.value) ((a.value+a.unc)+b.value)
  let lostB := !changed (a.value+b.value) (a.value+(b.value+b.unc))
  IO.println s!"SELECTOR clean={Adequacy32.isAdequate c} lostA={lostA} lostB={lostB}"
  unless Adequacy32.absorbed one half && !(Adequacy32.absorbed next half) do
    throw (IO.userError "tie controls failed")
  unless Adequacy32.isAdequate c && lostA && !lostB do
    throw (IO.userError "selector witness absent")
