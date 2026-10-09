import NavierStokes.SmoothFamilyTorusInverse

/-!
# A precise route to the manuscript's four-derivative torus estimate

Unlike the V1 abstract scope separator, this file references the *actual*
directional inverse and Fourier-coefficient definitions in the pinned
OpenAI/NavierStokesAndEuler project.

The only additional assumption is summability of the third inverse power
on the actual frequency lattice Z x Z. That mathematical lemma is TRUE in
dimension two, but it must be proved under the pinned mathematics authority
before either theorem below is described as an unconditional 4-loss result.

No semantic claim about equivalence to the entire NL paper is made.
-/

noncomputable section

namespace MathGraph.FourLossBridge

open Set
open NavierStokes.TorusInverse
open NavierStokes.SmoothFamilyTorusInverse
open scoped Topology ContDiff BigOperators

/-- The exact missing two-dimensional lattice-summability obligation. -/
def SummableThirdLattice : Prop :=
  Summable (fun k : Frequency => (weight k ^ 3)⁻¹)

/-- Reuse the unchanged Fourier coefficient decay bound, but spend only
    3 additional derivatives, rather than 4, to pay for the lattice sum. -/
theorem coefficient_seminorm_bound_three
    (h3 : SummableThirdLattice)
    {f : Plane → ℂ} (hf : ContDiff ℝ ∞ f)
    (hp : NavierStokes.SmoothFourierData.UnitPeriodic f)
    (p : ℕ) {C : ℝ}
    (hzero : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1, ‖f (x, y)‖ ≤ C)
    (hfirst : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (p + 3) f (x, y)‖ ≤ C)
    (hsecond : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (p + 3)
        (NavierStokes.SmoothFourierData.swapFunction f) (x, y)‖ ≤ C) :
    coeffSeminorm p (NavierStokes.SmoothFourierData.coefficient f) ≤
      (3 ^ (p + 3) * C) * ∑' k : Frequency, (weight k ^ 3)⁻¹ := by
  have hb (k : Frequency) : weight k ^ p *
      ‖NavierStokes.SmoothFourierData.coefficient f k‖ ≤
      (3 ^ (p + 3) * C) * (weight k ^ 3)⁻¹ := by
    rw [← div_eq_mul_inv]
    apply (le_div_iff₀ (pow_pos (weight_pos k) 3)).mpr
    calc
      (weight k ^ p * ‖NavierStokes.SmoothFourierData.coefficient f k‖) *
          weight k ^ 3 =
          weight k ^ (p + 3) *
            ‖NavierStokes.SmoothFourierData.coefficient f k‖ := by
            rw [pow_add]; ring
      _ ≤ 3 ^ (p + 3) * C :=
        NavierStokes.SmoothFourierData.coefficient_polynomial_bound
          hf hp (p + 3) hzero hfirst hsecond k
  have h := (NavierStokes.SmoothFourierData.rapid_coefficient hf hp p).tsum_le_tsum
    hb (h3.mul_left (3 ^ (p + 3) * C))
  simpa only [coeffSeminorm, tsum_mul_left] using h

variable {P : Type} [NormedAddCommGroup P] [NormedSpace ℝ P] [FiniteDimensional ℝ P]

/-- Four-loss inverse bound for the *actual* smooth periodic source family,
    conditional only on the explicitly identified summable lattice weight.

    This is the pointwise derivativeWord estimate, not yet the paper's
    supremum norm statement for all multiindices <= m. -/
theorem inverse_four_loss_of_summable_third
    (h3 : SummableThirdLattice)
    (d : Direction) {f : Source P}
    (hf : ContDiff ℝ ∞ f) (hp : Periodic f)
    (w : List Bool) (p : P) (Y : Plane) {C : ℝ}
    (hzero : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖f (p, (x, y))‖ ≤ C)
    (hfirst : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (slice f p) (x, y)‖ ≤ C)
    (hsecond : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (NavierStokes.SmoothFourierData.swapFunction (slice f p)) (x, y)‖ ≤ C) :
    ‖derivativeWord w (slice (inverse d f) p) Y‖ ≤
      ((6 * ‖omega⁻¹‖) * ‖omega‖ ^ w.length) *
      ((3 ^ ((w.length + 1) + 3) * C) *
        ∑' k : Frequency, (weight k ^ 3)⁻¹) := by
  have hbound :=
    coefficient_seminorm_bound_three h3
      (slice_smooth hf p) (hp p) (w.length + 1) hzero
      (by simpa only [Nat.add_assoc, Nat.reduceAdd] using hfirst)
      (by simpa only [Nat.add_assoc, Nat.reduceAdd] using hsecond)
  exact (inverse_derivativeWord_bound d
    (NavierStokes.SmoothFourierData.rapid_coefficient (slice_smooth hf p) (hp p))
    w Y).trans (mul_le_mul_of_nonneg_left hbound (by positivity))

end MathGraph.FourLossBridge

#print axioms MathGraph.FourLossBridge.coefficient_seminorm_bound_three
#print axioms MathGraph.FourLossBridge.inverse_four_loss_of_summable_third
