import HTilt.CoordinateChecklist
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith

/-!
# Finite H-Tilt Coordinate Residual Envelope Exists

This fixture proves that every finite coordinate list admits some residual
envelope bound `B`.

This is still pre-spectral finite-coordinate real/list algebra. It does not
construct a tight maximum, does not choose a shift `c`, and does not prove
dominance.
-/

namespace HTiltCoordinateResidualEnvelopeExists

open HTilt.CoordinateChecklist

/--
Every finite coordinate list has some residual envelope.

The bound is built inductively using `max`. It is not claimed to be tight or
canonical.
-/
theorem residual_envelope_exists
    (a b : ℝ)
    (coords : List Coord) :
    ∃ B : ℝ, ResidualEnvelope a b B coords := by
  induction coords with
  | nil =>
      refine ⟨0, ?_⟩
      intro q hq
      cases hq
  | cons hd tl ih =>
      rcases ih with ⟨B, hB⟩
      refine ⟨max (residual a b hd) B, ?_⟩
      intro q hq
      simp at hq
      rcases hq with hq | hq
      · rw [hq]
        exact le_max_left (residual a b hd) B
      · exact le_trans (hB q hq) (le_max_right (residual a b hd) B)

end HTiltCoordinateResidualEnvelopeExists
