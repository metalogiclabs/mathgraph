import OAI.Computability.Logspace.Deterministic

/-!
# Finite configuration envelope for the pinned OAI Logspace machine
A finite code for state, input heads, bounded work heads and bounded tape window.

This is a representation/counting lemma, not yet a polynomial-time bound:
the work-window radius must first be linked to the OAI spaceThrough measure.
-/

namespace Metalogic.OpenAIMath.FiniteEnvelope

open OAI.ExactDerandomization

/-- All data needed when work heads and nonblank cells lie in [-s,s]. -/
structure Envelope (q w h n s : ℕ) where
  state : Fin (q + 1)
  inputPos : Fin h → Fin (n + 2)
  workPos : Fin w → Fin (2 * s + 1)
  work : Fin w → Fin (2 * s + 1) → Bool
  deriving Fintype

/-- The bounded encoding state space is genuinely finite. -/
theorem envelope_finite (q w h n s : ℕ) :
    Finite (Envelope q w h n s) := inferInstance

/-- Cardinality of the finite envelope is an explicit combinatorial product. -/
theorem envelope_card (q w h n s : ℕ) :
    Fintype.card (Envelope q w h n s) =
      (q + 1) * (n + 2) ^ h * (2 * s + 1) ^ w *
        2 ^ (w * (2 * s + 1)) := by
  simp only [Envelope, Fintype.card_fun, Fintype.card_fin, Fintype.card_bool]
  ring

/-- If two OAI configurations agree on their finite data and all tape cells
inside [-s,s] and are blank outside that interval, they are identical. -/
theorem configuration_ext_of_window
    {q w h n s : ℕ} (c d : Configuration q w h n)
    (hstate : c.state = d.state)
    (hinput : c.inputPos = d.inputPos)
    (hpositions : c.workPos = d.workPos)
    (hinside : ∀ k z, -(s : ℤ) ≤ z → z ≤ (s : ℤ) →
      c.work k z = d.work k z)
    (houtc : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      c.work k z = false)
    (houtd : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      d.work k z = false) : c = d := by
  have hwork : c.work = d.work := by
    funext k z
    by_cases inside : -(s : ℤ) ≤ z ∧ z ≤ (s : ℤ)
    · exact hinside k z inside.1 inside.2
    · have outside : z < -(s : ℤ) ∨ (s : ℤ) < z := by omega
      rw [houtc k z outside, houtd k z outside]
  cases c
  cases d
  cases hstate
  cases hinput
  cases hpositions
  cases hwork
  rfl

end Metalogic.OpenAIMath.FiniteEnvelope
