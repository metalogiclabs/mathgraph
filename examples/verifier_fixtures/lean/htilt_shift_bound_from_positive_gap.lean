import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Finite H-Tilt Shift Bound From Positive Gap

This fixture proves a pure real/list algebra corollary:

If every finite competitor has real-part gap at least `δ`, every residual is
bounded by `B`, and `B < 2*c*δ` with `c ≥ 0`, then every competitor is
dominated after the real shift `c`.

It does not mention matrices, spectra, eigenvalues, Perron--Frobenius,
irreducibility, convergence, or empirical claims.
-/

namespace HTiltShiftBoundFromPositiveGap

/-- Squared modulus of `(c + a) + ib`, represented over reals. -/
def shiftedSqMod (c a b : ℝ) : ℝ :=
  (c + a)^2 + b^2

/-- Difference of squared shifted moduli. -/
theorem shiftedSqMod_sub_eq
    (c a b u v : ℝ) :
    shiftedSqMod c a b - shiftedSqMod c u v
      =
    2 * c * (a - u) + ((a^2 + b^2) - (u^2 + v^2)) := by
  unfold shiftedSqMod
  ring

/-- Single-pair sufficient condition for shifted modulus dominance. -/
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
Shared-envelope finite-list version.

If `B` bounds every residual and `B` lies below every shift gap, then every
finite competitor is dominated after shifting.
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

/--
Positive-gap bound.

If every competitor has real-part gap at least `δ`, every residual is bounded
by `B`, `c ≥ 0`, and `B < 2*c*δ`, then every competitor is dominated after the
shift.

This gives a single computable shift inequality before introducing actual
matrix spectra.
-/
theorem shiftedSqMod_gt_for_all_competitors_of_positive_gap
    (c a b B δ : ℝ)
    (competitors : List (ℝ × ℝ))
    (c_nonneg : 0 ≤ c)
    (residual_bound :
      ∀ p ∈ competitors,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (gap_bound :
      ∀ p ∈ competitors,
        δ ≤ a - p.1)
    (shift_bound :
      B < 2 * c * δ) :
    ∀ p ∈ competitors,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  apply shiftedSqMod_gt_for_all_competitors_of_shared_bound
  · exact residual_bound
  · intro p hp
    have hle : 2 * c * δ ≤ 2 * c * (a - p.1) := by
      nlinarith [c_nonneg, gap_bound p hp]
    exact lt_of_lt_of_le shift_bound hle

end HTiltShiftBoundFromPositiveGap
