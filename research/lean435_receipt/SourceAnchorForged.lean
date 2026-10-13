/- Identical source authority, but the local statement has been replaced
   together with the proof. A valid forged pair MUST fail this anchor. -/
import Lean
import ForgedSolution

open Lean Elab Command

run_cmd do
  let env ← getEnv
  let some original := env.find? ``Nat.gcd_comm
    | throwError "SOURCE_DECLARATION_NOT_FOUND"
  let some candidate := env.find? ``MathGraphReceipt.upstream_gcd_comm
    | throwError "CANDIDATE_DECLARATION_NOT_FOUND"
  let same ← liftTermElabM <| Lean.Meta.isDefEq original.type candidate.type
  unless same do
    throwError "SOURCE_STATEMENT_MISMATCH"
  logInfo "SOURCE_STATEMENT_MATCH"
