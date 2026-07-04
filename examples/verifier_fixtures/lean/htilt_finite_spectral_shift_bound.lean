import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Finite H-Tilt Finite Spectral Shift Bound

This fixture lifts the single-pair shifted squared-modulus dominance theorem
to a finite list of competitors.

It remains pure real/list algebra. It does not mention matrices, eigenvalues,
Perron--Frobenius, irreducibility, convergence, or empirical claims.
-/

namespace HTiltFiniteSpectralShiftBound

/-- Squared modulus of `(c + a) + ib`, represented over reals. -/
def shiftedSqMod (c a b : ℝ) : ℝ :=
  (c + a)^2 + b^2

/--
Difference of squared shifted moduli.

This is the algebraic identity:

`shiftedSqMod c a b - shiftedSqMod c u v =
  2*c*(a-u) + ((a^2+b^2) - (u^2+v^2))`.
-/
theorem shiftedSqMod_sub_eq
    (c a b u v : ℝ) :
    shiftedSqMod c a b - shiftedSqMod c u v
      =
    2 * c * (a - u) + ((a^2 + b^2) - (u^2 + v^2)) := by
  unfold shiftedSqMod
  ring

/--
Single-pair sufficient condition for shifted modulus dominance.
-/
theorem shiftedSqMod_gt_of_bound
    (c a b u v : ℝ)
    (bound :
      |(u^2 + v^2) - (a^2 + b^2)| < 2 * c * (a - u)) :
    shiftedSqMod c u v < shiftedSqMod c a b := by
  have hdiff :
      shiftedSqMod c a b - shiftedSqMod c u v
        =
      2 * c * (a - u) - ((u^2 + v^2) - (a^2 + b^2)) := by
    rw [shiftedSqMod_sub_eq]
    ring
  have hlt :
      (u^2 + v^2) - (a^2 + b^2)
        <
      2 * c * (a - u) := by
    exact lt_of_le_of_lt (le_abs_self ((u^2 + v^2) - (a^2 + b^2))) bound
  have hpos :
      0 < 2 * c * (a - u) - ((u^2 + v^2) - (a^2 + b^2)) := by
    linarith
  have :
      0 < shiftedSqMod c a b - shiftedSqMod c u v := by
    rw [hdiff]
    exact hpos
  linarith

/--
Finite-list lift.

If every competitor in a finite list satisfies the single-pair residual bound,
then every competitor in that list has strictly smaller shifted squared modulus.
-/
theorem shiftedSqMod_gt_for_all_competitors
    (c a b : ℝ)
    (competitors : List (ℝ × ℝ))
    (bound :
      ∀ p ∈ competitors,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| < 2 * c * (a - p.1)) :
    ∀ p ∈ competitors,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  intro p hp
  exact shiftedSqMod_gt_of_bound c a b p.1 p.2 (bound p hp)

/--
Finite-list lift with an explicit shared scalar envelope.

If a scalar `B` bounds every unshifted squared-modulus residual, and for every
competitor this shared `B` is strictly below the corresponding shift gap
`2*c*(a-u)`, then every competitor is dominated after the shift.

This is the finite-bound abstraction needed before introducing actual spectra.
-/
theorem shiftedSqMod_gt_for_all_competitors_of_shared_bound
    (c a b B : ℝ)
    (competitors : List (ℝ × ℝ))
    (residual_bound :
      ∀ p ∈ competitors,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (shift_gap_bound :
      ∀ p ∈ competitors,
        B < 2 * c * (a - p.1)) :
    ∀ p ∈ competitors,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  intro p hp
  apply shiftedSqMod_gt_of_bound
  exact lt_of_le_of_lt (residual_bound p hp) (shift_gap_bound p hp)

end HTiltFiniteSpectralShiftBound
