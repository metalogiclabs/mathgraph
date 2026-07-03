import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Finite H-Tilt Spectral Shift Order

This fixture proves the real algebraic core behind spectral-abscissa-to-radius
alignment after a large real shift.

It does not mention matrices, Perron--Frobenius, irreducibility, convergence,
or empirical claims.
-/

namespace HTiltSpectralShiftOrder

/-- Squared modulus of `(c + a) + ib`, represented over reals. -/
def shiftedSqMod (c a b : ℝ) : ℝ :=
  (c + a)^2 + b^2

/--
Difference of squared shifted moduli.

This is the algebraic identity:

`|(c+λ)|^2 - |(c+μ)|^2 =
  2c(Re λ - Re μ) + (|λ|^2 - |μ|^2)`

written with λ = a+ib and μ = u+iv.
-/
theorem shiftedSqMod_sub_eq
    (c a b u v : ℝ) :
    shiftedSqMod c a b - shiftedSqMod c u v
      =
    2 * c * (a - u) + ((a^2 + b^2) - (u^2 + v^2)) := by
  unfold shiftedSqMod
  ring

/--
Lean-friendly sufficient condition for shifted modulus dominance.

If the shift term dominates the absolute unshifted squared-modulus difference,
then the shifted λ-modulus is strictly larger than the shifted μ-modulus.
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

end HTiltSpectralShiftOrder
