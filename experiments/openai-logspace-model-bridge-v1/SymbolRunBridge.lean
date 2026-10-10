import SymbolStepSimulation

/-!
Reusable induction from exact one-step simulation to every finite run.
The theorem explicitly ASSUMES initial and step commutation; those two
premises must be discharged before any cross-model adequacy promotion.
-/

namespace Metalogic.OpenAIMath.SymbolRunBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge
open Metalogic.OpenAIMath.SymbolStepSimulation

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

def sourceRun (M : SymbolMachine α q w h) (blank : α)
    (x : Word) (coins : CoinTape) :
    ℕ → SymbolConfiguration α q w h x.length
  | 0 => sourceInitial M blank x.length
  | t + 1 => sourceStep M x (coins t) (sourceRun M blank x coins t)

/-- A verified source-initialization and one-step commuting law together imply
exact configuration correspondence at ALL finite execution times. -/
theorem run_commutes_of_initial_and_step
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (coins : CoinTape)
    (hinitial :
      encodeConfiguration codec (sourceInitial M codec.blank x.length) =
        (compileMachine codec M).initial x.length)
    (hstep : ∀ (b : Bool) (c : SymbolConfiguration α q w h x.length),
      encodeConfiguration codec (sourceStep M x b c) =
        (compileMachine codec M).step x b (encodeConfiguration codec c))
    (t : ℕ) :
    encodeConfiguration codec (sourceRun M codec.blank x coins t) =
      (compileMachine codec M).run x coins t := by
  induction t with
  | zero => exact hinitial
  | succ t ih =>
      change encodeConfiguration codec
        (sourceStep M x (coins t) (sourceRun M codec.blank x coins t)) =
          (compileMachine codec M).step x (coins t)
            ((compileMachine codec M).run x coins t)
      rw [hstep (coins t) (sourceRun M codec.blank x coins t), ih]

end Metalogic.OpenAIMath.SymbolRunBridge
