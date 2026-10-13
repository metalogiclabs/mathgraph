/- Independently compare imported original declaration's elaborated type
   to the generated local theorem's elaborated type. The imported declaration
   is compiled from the pinned Lean v4.35.0 upstream release; CI separately
   checks the exact original source Git blob.
-/
import Lean
import Solution

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
