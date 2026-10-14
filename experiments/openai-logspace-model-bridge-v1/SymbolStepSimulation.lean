import SymbolStepBridge

/-!
One-step simulation for a separately defined finite-symbol operational machine.
This imports OpenAI's immutable Boolean-target Machine.step; no second
definition of OAI Machine.step is assumed or hidden.
-/

namespace Metalogic.OpenAIMath.SymbolStepSimulation

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolStepBridge

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- Direct source transition semantics (source symbols α, not Boolean tracks). -/
def sourceStep (M : SymbolMachine α q w h) (x : Word) (coin : Bool)
    (c : SymbolConfiguration α q w h x.length) :
    SymbolConfiguration α q w h x.length :=
  match M.output c.state with
  | some _ => c
  | none =>
    let a := M.transition c.state
      (fun j => readInput x (c.inputPos j))
      (fun k => c.work k (c.workPos k)) coin
    { state := a.nextState
      inputPos := fun j => (a.inputMove j).moveInput (c.inputPos j)
      workPos := fun k => (a.workMove k).move (c.workPos k)
      work := writeAllSource c.work c.workPos a.write }

/-- Complete initial source-symbol configuration: uniform blank work tapes. -/
def sourceInitial (M : SymbolMachine α q w h) (blank : α) (n : ℕ) :
    SymbolConfiguration α q w h n where
  state := M.initialState
  inputPos := fun _ => ⟨0, by omega⟩
  workPos := fun _ => 0
  work := fun _ _ => blank

/-- Encoding the source initialization agrees with the actual OAI initialization. -/
theorem initial_commutes (codec : AlphabetCodec α K)
    (M : SymbolMachine α q w h) (n : ℕ) :
    encodeConfiguration codec (sourceInitial M codec.blank n) =
      (compileMachine codec M).initial n := by
  simp only [encodeConfiguration, sourceInitial, Machine.initial, compileMachine]
  congr 1
  funext j z
  simp [encodeTracks, encodeSymbol]

/-- Encoding a source-symbol write gives exactly the Boolean-target
    Function.update operation at the corresponding copied work-head. -/
theorem write_commutes_with_OAI_update
    (codec : AlphabetCodec α K)
    {n : ℕ} (c : SymbolConfiguration α q w h n)
    (write : Fin w → α) :
    encodeTracks codec.indices codec.blank
        (writeAllSource c.work c.workPos write) =
      (fun j : Fin (w * K) =>
         Function.update (encodeTracks codec.indices codec.blank c.work j)
           (c.workPos ((finProdFinEquiv (m := w) (n := K)).symm j).1)
           (encodeSymbol codec.indices codec.blank
             (write ((finProdFinEquiv (m := w) (n := K)).symm j).1)
             ((finProdFinEquiv (m := w) (n := K)).symm j).2)) := by
  rw [encodeTracks_writeAll_commutes]
  funext j z
  simp [writeAllEncoded, Function.update]

end Metalogic.OpenAIMath.SymbolStepSimulation
