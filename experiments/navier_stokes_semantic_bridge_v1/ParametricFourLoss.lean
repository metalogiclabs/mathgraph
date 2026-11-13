import FourLossUnconditional

/-!
V7 source-pinned bridge: all parameter-jet orders q and mixed torus
coordinate derivative words w of the ACTUAL OpenAI inverse.

This intentionally copies the proof structure of
NavierStokes.SmoothFamilyTorusInverse.mixedJet_inverse_bound, changing
only the underlying proved derivative-word estimate from loss 5 to loss 4
and using the already proved two-dimensional lattice inverse-cube sum.

This is not a full all-parameter/torus Fréchet JetBound C^m theorem, nor
a blanket endorsement of the prose interpretation of the manuscript.
-/

noncomputable section

namespace MathGraph.ParametricFourLoss

open Set
open NavierStokes.TorusInverse
open NavierStokes.SmoothFamilyTorusInverse
open scoped Topology ContDiff BigOperators

noncomputable def fourLossConstant (r : ℕ) : ℝ :=
  ((6 * ‖omega⁻¹‖) * ‖omega‖ ^ r) *
    (3 ^ ((r + 1) + 3) * ∑' k : Frequency, (weight k ^ 3)⁻¹)

theorem fourLossConstant_nonneg (r : ℕ) : 0 ≤ fourLossConstant r := by
  unfold fourLossConstant
  have hs : 0 ≤ ∑' k : Frequency, (weight k ^ 3)⁻¹ :=
    tsum_nonneg (fun k => inv_nonneg.mpr (pow_nonneg (weight_pos k).le _))
  positivity

variable {P : Type} [NormedAddCommGroup P] [NormedSpace ℝ P]
  [FiniteDimensional ℝ P]

/-- Uniform bound for the ACTUAL inverse's parameter jets q and mixed torus
derivative word w. Both pure input torus jet obligations have order |w|+4.
The finite constant is independent of f, p, Y, v, and the parameter set. -/
theorem mixedJet_inverse_bound_four
    (d : Direction) {f : Source P}
    (hf : ContDiff ℝ ∞ f) (hp : Periodic f) (q : ℕ) (w : List Bool)
    (S : Set P) {C : ℝ} (hC : 0 ≤ C)
    (hzero : ∀ p ∈ S, ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖parameterJet q f (p, (x, y))‖ ≤ C)
    (hfirst : ∀ p ∈ S, ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖tensorTorusWord (List.replicate (w.length + 4) false)
        (fun Y => parameterJet q f (p, Y)) (x, y)‖ ≤ C)
    (hsecond : ∀ p ∈ S, ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖tensorTorusWord (List.replicate (w.length + 4) false)
        (fun Y => parameterJet q f (p, (Y.2, Y.1))) (x, y)‖ ≤ C)
    (p : P) (hps : p ∈ S) (Y : Plane) :
    ‖mixedJet q w (inverse d f) (p, Y)‖ ≤ fourLossConstant w.length * C := by
  apply ContinuousMultilinearMap.opNorm_le_bound
    (mul_nonneg (fourLossConstant_nonneg w.length) hC)
  intro v
  rw [mixedJet_apply (inverse_smooth d hf hp),
    parameterJetApply_inverse d hf hp]
  have hg : ContDiff ℝ ∞ (fun Y => parameterJet q f (p, Y)) :=
    (parameterJet_smooth hf q).comp (contDiff_const.prodMk contDiff_id)
  have hgs : ContDiff ℝ ∞ (fun Y : Plane => parameterJet q f (p, (Y.2, Y.1))) :=
    hg.comp (contDiff_snd.prodMk contDiff_fst)
  let L := ContinuousMultilinearMap.apply ℝ (fun _ : Fin q => P) ℂ v
  have hb0 : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖parameterJetApply q v f (p, (x, y))‖ ≤ C * ∏ i, ‖v i‖ := by
    intro x hx y hy
    exact ContinuousMultilinearMap.le_of_opNorm_le (hzero p hps x hx y hy) v
  have hb1 : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (slice (parameterJetApply q v f) p) (x, y)‖ ≤ C * ∏ i, ‖v i‖ := by
    intro x hx y hy
    have he := congrFun (tensorTorusWord_map L hg
      (List.replicate (w.length + 4) false)) (x, y)
    rw [tensorTorusWord_replicate] at he
    change NavierStokes.SmoothFourierData.xJet (w.length + 4)
      (slice (parameterJetApply q v f) p) (x, y) =
      (tensorTorusWord (List.replicate (w.length + 4) false)
        (fun Y => parameterJet q f (p, Y)) (x, y)) v at he
    rw [he]
    exact ContinuousMultilinearMap.le_of_opNorm_le (hfirst p hps x hx y hy) v
  have hb2 : ∀ x ∈ Icc (0 : ℝ) 1, ∀ y ∈ Icc (0 : ℝ) 1,
      ‖NavierStokes.SmoothFourierData.xJet (w.length + 4)
        (NavierStokes.SmoothFourierData.swapFunction
          (slice (parameterJetApply q v f) p)) (x, y)‖ ≤
        C * ∏ i, ‖v i‖ := by
    intro x hx y hy
    have he := congrFun (tensorTorusWord_map L hgs
      (List.replicate (w.length + 4) false)) (x, y)
    rw [tensorTorusWord_replicate] at he
    change NavierStokes.SmoothFourierData.xJet (w.length + 4)
      (NavierStokes.SmoothFourierData.swapFunction
        (slice (parameterJetApply q v f) p)) (x, y) =
      (tensorTorusWord (List.replicate (w.length + 4) false)
        (fun Y => parameterJet q f (p, (Y.2, Y.1))) (x, y)) v at he
    rw [he]
    exact ContinuousMultilinearMap.le_of_opNorm_le (hsecond p hps x hx y hy) v
  exact (MathGraph.FourLossComplete.actual_inverse_four_loss d
    (parameterJetApply_smooth hf q v) (parameterJetApply_periodic hf hp q v)
    w p Y hb0 hb1 hb2).trans_eq (by
      dsimp [fourLossConstant]
      ring)

end MathGraph.ParametricFourLoss

#print axioms MathGraph.ParametricFourLoss.fourLossConstant_nonneg
#print axioms MathGraph.ParametricFourLoss.mixedJet_inverse_bound_four
