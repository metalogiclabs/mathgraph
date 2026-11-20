import Lean

open Lean Meta

-- Exact addDecl operation used by the pinned CptCopy command.  A theorem
-- with a mismatched type MUST be rejected by the kernel.
run_meta do
  let some (.thmInfo t) := (← getEnv).find? ``Nat.add_zero
    | throwError "missing Nat.add_zero theorem"
  addDecl (.thmDecl { t with name := `direct_add_false_attack, type := mkConst ``False })

#check direct_add_false_attack
