import LeftWallCompiler

/-!
# Fused initialization for a genuinely left-bounded work tape

Unlike the two-track compiler with a marker-only startup, this compiler
initializes the permanent origin marker while executing the *first* source
transition using the *same* coin. It therefore targets same-clock execution
for every positive clock, avoiding an extraneous randomized bootstrap bit.

The zero-time OAI startup state is intentionally not asserted equal to a
source active configuration. Full trace and probability transfer remain
separate, explicit proof obligations.
-/

namespace Metalogic.OpenAIMath.LeftWallFusedCompiler

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler

variable {q h : ℕ}

/-- The marker is set at the source's origin in its first simulated
transition, rather than spending an entire additional machine step. -/
def compileFused (M : LeftMachine q h) : Machine (q + 1) 2 h where
  initialState := startupState q
  output := fun st =>
    match decodeActive st with
    | none => none
    | some sourceState => M.output sourceState
  transition := fun st inp read coin =>
    match decodeActive st with
    | none =>
      match M.output M.initialState with
      | some _ =>
        { nextState := activeState M.initialState
          write := fun j => decide (j.val = 1)
          workMove := fun _ => .stay
          inputMove := fun _ => .stay }
      | none =>
        let a := M.transition M.initialState inp false coin
        { nextState := activeState a.nextState
          write := fun j => if j.val = 0 then a.write else true
          workMove := fun _ => guardedMove a.workMove true
          inputMove := a.inputMove }
    | some sourceState =>
      let a := M.transition sourceState inp (read 0) coin
      { nextState := activeState a.nextState
        write := fun j => if j.val = 0 then a.write else read 1
        workMove := fun _ => guardedMove a.workMove (read 1)
        inputMove := a.inputMove }

/-- After initialization, the fused compiler and the marker-only compiler
have literally the same transition table on encoded active states. -/
theorem active_transition_identical
    (M : LeftMachine q h) (st : Fin (q + 1))
    (inp : Fin h → InputSymbol) (read : Fin 2 → Bool) (coin : Bool) :
    (compileFused M).transition (activeState st) inp read coin =
      (compile M).transition (activeState st) inp read coin := by
  simp [compileFused, compile, decodeActive_active]

theorem fused_output_active
    (M : LeftMachine q h) (st : Fin (q + 1)) :
    (compileFused M).output (activeState st) = M.output st := by
  simp [compileFused, decodeActive_active]

theorem fused_output_startup (M : LeftMachine q h) :
    (compileFused M).output (startupState q) = none := by
  simp [compileFused, decodeActive_startup]

/-- The initial source work tape is blank, so the OAI startup transition can
read the work symbol without pre-initializing any data track. -/
theorem source_initial_read_blank
    (M : LeftMachine q h) (n : ℕ) :
    (LeftBoundedMachine.initial M n).work
      (LeftBoundedMachine.initial M n).workPos = false := by
  rfl

/-- The synchronized marker-protected motion from source position zero
has the same outcome as the one-sided work-head transition. -/
theorem fused_bootstrap_move_correct (d : Direction) :
    (guardedMove d true).move (0 : ℤ) =
      (moveNat d 0 : ℤ) := by
  cases d <;> decide

end Metalogic.OpenAIMath.LeftWallFusedCompiler
