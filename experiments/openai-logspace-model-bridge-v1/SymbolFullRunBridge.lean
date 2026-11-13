import SymbolOneStepBridge

/-!
Discharges the separately checked conditional run-simulation interface using
the actual initial-state and complete one-step correspondence.
If SymbolOneStepBridge fails, this theorem cannot compile or be promoted.
-/

namespace Metalogic.OpenAIMath.SymbolFullRunBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolStepSimulation
open Metalogic.OpenAIMath.SymbolOneStepBridge
open Metalogic.OpenAIMath.SymbolRunBridge

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- Full trace of the independently specified finite-symbol machine is
identical to the bit-track machine's full trace after lossless encoding. -/
theorem compiled_run_commutes
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coins : CoinTape) (t : ℕ) :
    encodeConfiguration codec (sourceRun M codec.blank x coins t) =
      (compileMachine codec M).run x coins t := by
  exact run_commutes_of_initial_and_step codec M x coins
    (initial_commutes codec M x.length)
    (fun b c => source_step_commutes codec M x b c) t

end Metalogic.OpenAIMath.SymbolFullRunBridge
