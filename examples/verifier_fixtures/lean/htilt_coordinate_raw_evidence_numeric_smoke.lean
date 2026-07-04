import HTilt.CoordinateChecklist
import Mathlib.Tactic.NormNum

/-!
# Finite H-Tilt Coordinate Raw Evidence Numeric Smoke

A concrete singleton raw-evidence example for the reusable
`HTilt.CoordinateChecklist` core.

Target coordinate: `(2, 0)`
Competitor list: `[(0, 0)]`
Residual bound: `B = 4`
Strict gap: `δ = 1`
Shift: `c = 3`

The resulting shifted squared-modulus comparison is `9 < 25`.

This is a smoke test only. It is pre-spectral finite-coordinate real/list
algebra and does not claim that the coordinates are eigenvalues.
-/

namespace HTiltCoordinateRawEvidenceNumericSmoke

open HTilt.CoordinateChecklist

/--
A concrete singleton raw-evidence smoke theorem.

The raw residual evidence is `|(0^2 + 0^2) - (2^2 + 0^2)| ≤ 4`.
The raw strict-gap evidence is `0 ≤ 2 - 1`.
The scalar side condition is `4 / (2 * 1) < 3`.
-/
theorem numeric_singleton_raw_evidence_smoke :
    ∀ p ∈ [((0 : ℝ), (0 : ℝ))],
      shiftedSqMod 3 p.1 p.2 < shiftedSqMod 3 2 0 := by
  apply finite_coordinate_shifted_dominance_from_raw_evidence
    (c := 3) (a := 2) (b := 0) (B := 4) (δ := 1)
    (coords := [((0 : ℝ), (0 : ℝ))])
  · intro p hp
    simp at hp
    rw [hp]
    norm_num [residual]
  · intro p hp
    simp at hp
    rw [hp]
    norm_num
  · norm_num
  · norm_num
  · norm_num

end HTiltCoordinateRawEvidenceNumericSmoke
