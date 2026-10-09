import LeftWallFusedCompiler

/-!
# Exact first-step equality for the left-bounded source and fused-marker OAI target

Unlike a conditional encoding, the target's first step is checked against
the real source step with the same input and coin bit, including infinite tape
functions and both synchronized work-head coordinates.
-/

namespace Metalogic.OpenAIMath.LeftWallSimulation

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler

variable {q h : ℕ}

/-- Record equality follows from equality of each protected configuration
field; no observational quotient is substituted for complete equality. -/
theorem configuration_eq_of_fields
    {n : ℕ} (a b : Configuration (q + 1) 2 h n)
    (hs : a.state = b.state)
    (hi : a.inputPos = b.inputPos)
    (hp : a.workPos = b.workPos)
    (hw : a.work = b.work) : a = b := by
  cases a
  cases b
  cases hs
  cases hi
  cases hp
  cases hw
  rfl

/-- The *whole* fused bootstrap target configuration should equal the source
configuration after its first transition, for both initially halted and
active sources. This includes work tapes as functions on all coordinates. -/
theorem first_step_commutes
    (M : LeftMachine q h) (x : Word) (coin : Bool) :
    (compileFused M).step x coin ((compileFused M).initial x.length) =
      encode (LeftBoundedMachine.step M x coin
        (LeftBoundedMachine.initial M x.length)) := by
  apply configuration_eq_of_fields
  · simpa [encode] using first_step_control_commutes M x coin
  · funext j
    cases ho : M.output M.initialState with
    | some b =>
        simp [Machine.step, LeftBoundedMachine.step,
          Machine.initial, LeftBoundedMachine.initial, compileFused,
          decodeActive, startupState, encode, ho]
    | none =>
        simp [Machine.step, LeftBoundedMachine.step,
          Machine.initial, LeftBoundedMachine.initial, compileFused,
          decodeActive, startupState, encode, ho]
  · funext j
    cases ho : M.output M.initialState with
    | some b =>
        simp [Machine.step, LeftBoundedMachine.step,
          Machine.initial, LeftBoundedMachine.initial, compileFused,
          decodeActive, startupState, encode, Direction.move, ho]
    | none =>
        simpa [Machine.step, LeftBoundedMachine.step,
          Machine.initial, LeftBoundedMachine.initial, compileFused,
          decodeActive, startupState, encode, ho]
          using (fused_bootstrap_move_correct
            ((M.transition M.initialState
              (fun k => readInput x (⟨0, by omega⟩ : Fin (x.length + 2)))
              false coin).workMove))
  · funext j z
    fin_cases j
    · cases ho : M.output M.initialState with
      | some b =>
          simp [Machine.step, LeftBoundedMachine.step,
            Machine.initial, LeftBoundedMachine.initial, compileFused,
            decodeActive, startupState, encode, Function.update,
            extendWork, ho]
      | none =>
          simpa [Machine.step, LeftBoundedMachine.step,
            Machine.initial, LeftBoundedMachine.initial, compileFused,
            decodeActive, startupState, encode, ho]
            using congrFun
              (initial_data_write_commutes
                ((M.transition M.initialState
                  (fun k => readInput x (⟨0, by omega⟩ : Fin (x.length + 2)))
                  false coin).write)).symm z
    · cases ho : M.output M.initialState with
      | some b =>
          simpa [Machine.step, LeftBoundedMachine.step,
            Machine.initial, LeftBoundedMachine.initial, compileFused,
            decodeActive, startupState, encode, ho]
            using congrFun origin_marker_from_blank z
      | none =>
          simpa [Machine.step, LeftBoundedMachine.step,
            Machine.initial, LeftBoundedMachine.initial, compileFused,
            decodeActive, startupState, encode, ho]
            using congrFun origin_marker_from_blank z

end Metalogic.OpenAIMath.LeftWallSimulation
