import VisitedRadius

/-!
Window encoding maps concrete OAI configurations to a finite-memory envelope.
Faithfulness is proved under checked bounded-head and blank-exterior hypotheses.
The next gate instantiates those hypotheses from spaceThrough.
-/

namespace Metalogic.OpenAIMath.WindowEncoding

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.FiniteEnvelope

/-- Saturating coordinate encoder, injective on the intended signed window. -/
def windowIndex (s : ℕ) (z : ℤ) : Fin (2 * s + 1) :=
  ⟨min (z + (s : ℤ)).toNat (2 * s), by omega⟩

/-- Decode a finite work position back into a signed integer coordinate. -/
def windowCoord (s : ℕ) (i : Fin (2 * s + 1)) : ℤ :=
  (i.val : ℤ) - (s : ℤ)

/-- Every coordinate in [-s,s] survives the finite encoding unchanged. -/
theorem windowCoord_index (s : ℕ) (z : ℤ)
    (hlo : -(s : ℤ) ≤ z) (hhi : z ≤ (s : ℤ)) :
    windowCoord s (windowIndex s z) = z := by
  unfold windowCoord windowIndex
  simp
  omega

theorem windowIndex_injective_on_window (s : ℕ) (a b : ℤ)
    (ha0 : -(s : ℤ) ≤ a) (ha1 : a ≤ (s : ℤ))
    (hb0 : -(s : ℤ) ≤ b) (hb1 : b ≤ (s : ℤ))
    (heq : windowIndex s a = windowIndex s b) : a = b := by
  have h := congrArg (windowCoord s) heq
  simpa [windowCoord_index s a ha0 ha1, windowCoord_index s b hb0 hb1] using h

/-- A total finite code; equality is only sound on bounded configurations. -/
def encode (s : ℕ) {q w h n : ℕ}
    (c : Configuration q w h n) : Envelope q w h n s where
  state := c.state
  inputPos := c.inputPos
  workPos := fun k => windowIndex s (c.workPos k)
  work := fun k i => c.work k (windowCoord s i)

/-- Concrete bounded configurations having the same finite code are equal. -/
theorem encode_faithful_under_window
    {q w h n s : ℕ} (c d : Configuration q w h n)
    (hc : ∀ k, -(s : ℤ) ≤ c.workPos k ∧ c.workPos k ≤ (s : ℤ))
    (hd : ∀ k, -(s : ℤ) ≤ d.workPos k ∧ d.workPos k ≤ (s : ℤ))
    (houtc : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      c.work k z = false)
    (houtd : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      d.work k z = false)
    (heq : encode s c = encode s d) : c = d := by
  have hs : c.state = d.state := by
    simpa [encode] using
      (congrArg (fun e : Envelope q w h n s => e.state) heq)
  have hi : c.inputPos = d.inputPos := by
    simpa [encode] using
      (congrArg (fun e : Envelope q w h n s => e.inputPos) heq)
  have hp : c.workPos = d.workPos := by
    funext k
    apply windowIndex_injective_on_window s
      (c.workPos k) (d.workPos k)
      (hc k).1 (hc k).2 (hd k).1 (hd k).2
    simpa [encode] using
      (congrArg (fun e : Envelope q w h n s => e.workPos k) heq)
  have hw : ∀ k z, -(s : ℤ) ≤ z → z ≤ (s : ℤ) →
      c.work k z = d.work k z := by
    intro k z hlo hhi
    have hf :=
      congrArg (fun e : Envelope q w h n s => e.work k (windowIndex s z)) heq
    simpa [encode, windowCoord_index s z hlo hhi] using hf
  exact configuration_ext_of_window c d hs hi hp hw houtc houtd

end Metalogic.OpenAIMath.WindowEncoding
