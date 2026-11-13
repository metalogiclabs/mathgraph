import SymbolMachineBridge

/-!
A *separately authored* one-step simulation boundary for the pinned OpenAI
finite Boolean-track machine model. The representation remains exact and
does not identify the OAI model with every conventional Turing-machine model.
-/

namespace Metalogic.OpenAIMath.SymbolStepBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge
open Metalogic.OpenAIMath.SymbolMachineBridge

variable {α : Type} [DecidableEq α] {K q w h n : ℕ}

/-- Source finite-symbol configuration; unlike OAI work tapes, cells contain α. -/
structure SymbolConfiguration (α : Type) (q w h n : ℕ) where
  state : Fin (q + 1)
  inputPos : Fin h → Fin (n + 2)
  workPos : Fin w → ℤ
  work : Fin w → ℤ → α

/-- Encode every source tape cell into K Boolean tracks with copied head positions. -/
def encodeConfiguration (codec : AlphabetCodec α K)
    (c : SymbolConfiguration α q w h n) : Configuration q (w * K) h n where
  state := c.state
  inputPos := c.inputPos
  workPos := fun j =>
    c.workPos ((finProdFinEquiv (m := w) (n := K)).symm j).1
  work := encodeTracks codec.indices codec.blank c.work

/-- The OAI machine reads a valid source configuration as an encoded symbol block. -/
theorem encoded_configuration_reads
    (codec : AlphabetCodec α K)
    (c : SymbolConfiguration α q w h n) :
    (fun j : Fin (w * K) =>
      (encodeConfiguration codec c).work j
        ((encodeConfiguration codec c).workPos j)) =
    (fun j : Fin (w * K) =>
      let pair := (finProdFinEquiv (m := w) (n := K)).symm j
      encodeSymbol codec.indices codec.blank
        (c.work pair.1 (c.workPos pair.1)) pair.2) := by
  rfl

/-- Decoding what compiled OAI reads recovers the exact source work symbols. -/
theorem decode_encoded_configuration_reads
    (codec : AlphabetCodec α K)
    (c : SymbolConfiguration α q w h n) :
    (fun k : Fin w =>
      decodeTrackReads codec
        (fun j : Fin (w * K) =>
          (encodeConfiguration codec c).work j
            ((encodeConfiguration codec c).workPos j)) k) =
    (fun k => c.work k (c.workPos k)) := by
  rw [encoded_configuration_reads]
  funext k
  exact decodeTrackReads_encoded codec
    (fun k => c.work k (c.workPos k)) k

/-- On valid encoded observations, the compiled action equals the encoding of
    the original symbol-machine action: finite control and all writes/moves
    refer to the *same* source read and the same random bit. -/
theorem compileMachine_transition_encoded
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (st : Fin (q + 1)) (inp : Fin h → InputSymbol)
    (read : Fin w → α) (coin : Bool) :
    (compileMachine codec M).transition st inp
      (fun j : Fin (w * K) =>
        let pair := (finProdFinEquiv (m := w) (n := K)).symm j
        encodeSymbol codec.indices codec.blank (read pair.1) pair.2) coin =
    lowerAction codec.indices codec.blank (M.transition st inp read coin) := by
  change lowerAction codec.indices codec.blank
      (M.transition st inp
        (decodeTrackReads codec
          (fun j : Fin (w * K) =>
            let pair := (finProdFinEquiv (m := w) (n := K)).symm j
            encodeSymbol codec.indices codec.blank (read pair.1) pair.2)) coin) =
    lowerAction codec.indices codec.blank (M.transition st inp read coin)
  have hread :
      (fun k : Fin w =>
        decodeTrackReads codec
          (fun j : Fin (w * K) =>
            let pair := (finProdFinEquiv (m := w) (n := K)).symm j
            encodeSymbol codec.indices codec.blank (read pair.1) pair.2) k) = read := by
    funext k
    exact decodeTrackReads_encoded codec read k
  have hr : decodeTrackReads codec
      (fun j : Fin (w * K) =>
        let pair := (finProdFinEquiv (m := w) (n := K)).symm j
        encodeSymbol codec.indices codec.blank (read pair.1) pair.2) = read := by
    funext k
    exact congrFun hread k
  rw [hr]

end Metalogic.OpenAIMath.SymbolStepBridge
