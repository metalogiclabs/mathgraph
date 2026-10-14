import ExplicitAlphabetBridge

/-!
A machine-lowering interface with an explicit computable decoder.
A complete machine-level simulation theorem remains a separate obligation.
-/

namespace Metalogic.OpenAIMath.SymbolMachineBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.ExplicitAlphabetBridge

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- Data supplied by an effective alphabet encoding. The decoder is total on
    all Boolean blocks and is correct on blocks produced by the encoder. -/
structure AlphabetCodec (α : Type) [DecidableEq α] (K : ℕ) where
  indices : α ≃ Fin K
  blank : α
  decode : (Fin K → Bool) → α
  decode_roundtrip : ∀ a : α,
    decode (encodeSymbol indices blank a) = a

/-- A finite-alphabet machine with the same control, input and output
    interface as the OAI machine but a general finite work alphabet. -/
structure SymbolMachine (α : Type) (q w h : ℕ) where
  initialState : Fin (q + 1)
  output : Fin (q + 1) → Option Bool
  transition : Fin (q + 1) → (Fin h → InputSymbol) →
    (Fin w → α) → Bool → SymbolAction (α := α) q w h

/-- Decode the grouped K Boolean tracks into a source work-symbol read. -/
def decodeTrackReads (codec : AlphabetCodec α K) {w : ℕ}
    (bits : Fin (w * K) → Bool) (k : Fin w) : α :=
  codec.decode (fun i => bits (finProdFinEquiv (m := w) (n := K) (k, i)))

/-- Encode a source machine transition table directly into the
    OAI finite-Boolean-action interface. Invalid Boolean blocks are
    handled by the supplied total decoder; the decoding law is required
    only on blocks reachable from valid encoded source configurations. -/
def compileMachine (codec : AlphabetCodec α K)
    (M : SymbolMachine α q w h) : Machine q (w * K) h where
  initialState := M.initialState
  output := M.output
  transition := fun st inp bits coin =>
    lowerAction codec.indices codec.blank
      (M.transition st inp (decodeTrackReads codec bits) coin)

/-- Compiling a machine leaves the finite control initialization unchanged. -/
theorem compileMachine_initialState (codec : AlphabetCodec α K)
    (M : SymbolMachine α q w h) :
    (compileMachine codec M).initialState = M.initialState := rfl

/-- Compiling a machine leaves the halting/output interpretation unchanged. -/
theorem compileMachine_output (codec : AlphabetCodec α K)
    (M : SymbolMachine α q w h) :
    (compileMachine codec M).output = M.output := rfl

/-- The compiler's read interface recovers source symbols from
    correctly encoded simultaneous work-symbol observations. -/
theorem decodeTrackReads_encoded (codec : AlphabetCodec α K)
    (read : Fin w → α) (k : Fin w) :
    decodeTrackReads codec
      (fun j =>
        let p := (finProdFinEquiv (m := w) (n := K)).symm j
        encodeSymbol codec.indices codec.blank (read p.1) p.2) k
      = read k := by
  unfold decodeTrackReads
  have hbits :
      (fun i : Fin K =>
        (fun j : Fin (w * K) =>
          let p := (finProdFinEquiv (m := w) (n := K)).symm j
          encodeSymbol codec.indices codec.blank (read p.1) p.2)
          (finProdFinEquiv (m := w) (n := K) (k, i))) =
      encodeSymbol codec.indices codec.blank (read k) := by
    funext i
    exact congrArg
      (fun pair : Fin w × Fin K =>
        encodeSymbol codec.indices codec.blank (read pair.1) pair.2)
      ((finProdFinEquiv (m := w) (n := K)).left_inv (k, i))
  rw [hbits]
  exact codec.decode_roundtrip (read k)

end Metalogic.OpenAIMath.SymbolMachineBridge
