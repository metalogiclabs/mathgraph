import SymbolRunBridge

/-!
Main open OAI<->source finite-symbol one-step simulation lemma.
Unlike the conditional all-run induction, this MUST prove that the actual
OAI Machine.step agrees with independently defined sourceStep.
-/

namespace Metalogic.OpenAIMath.SymbolOneStepBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolStepSimulation

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- Exactly one source machine step is represented by exactly one target
    OAI Boolean-track machine step, including the halted branch. -/
theorem source_step_commutes
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coin : Bool) (c : SymbolConfiguration α q w h x.length) :
    encodeConfiguration codec (sourceStep M x coin c) =
      (compileMachine codec M).step x coin (encodeConfiguration codec c) := by
  have haction :
      (compileMachine codec M).transition c.state
        (fun j => readInput x (c.inputPos j))
        (fun j : Fin (w * K) =>
          (encodeConfiguration codec c).work j
            ((encodeConfiguration codec c).workPos j)) coin =
      lowerAction codec.indices codec.blank
        (M.transition c.state
          (fun j => readInput x (c.inputPos j))
          (fun k => c.work k (c.workPos k)) coin) := by
    rw [encoded_configuration_reads]
    exact compileMachine_transition_encoded codec M c.state
      (fun j => readInput x (c.inputPos j))
      (fun k => c.work k (c.workPos k)) coin
  have hwork :=
    write_commutes_with_OAI_update codec c
      (M.transition c.state
        (fun j => readInput x (c.inputPos j))
        (fun k => c.work k (c.workPos k)) coin).write
  cases ho : M.output c.state with
  | some answer =>
      simp [sourceStep, Machine.step, encodeConfiguration, compileMachine, ho]
  | none =>
      have houtput :
          (compileMachine codec M).output (encodeConfiguration codec c).state = none := by
        simpa [compileMachine, encodeConfiguration] using ho
      rw [Machine.step]
      simp only [houtput]
      simp only [encodeConfiguration] at haction ⊢
      have haction' :
          (compileMachine codec M).transition
            (encodeConfiguration codec c).state
            (fun j => readInput x ((encodeConfiguration codec c).inputPos j))
            (fun j : Fin (w * K) =>
              (encodeConfiguration codec c).work j
                ((encodeConfiguration codec c).workPos j)) coin =
          lowerAction codec.indices codec.blank
            (M.transition c.state
              (fun j => readInput x (c.inputPos j))
              (fun k => c.work k (c.workPos k)) coin) := by
        simpa only [encodeConfiguration] using haction
      rw [haction']
      simp only [sourceStep, ho]
      congr 1
      simpa [lowerAction, encodeTracks] using hwork

end Metalogic.OpenAIMath.SymbolOneStepBridge
