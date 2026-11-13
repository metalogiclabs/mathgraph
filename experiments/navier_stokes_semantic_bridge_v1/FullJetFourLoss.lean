import FourLossUnconditional

/-!
# Source-pinned V8: full joint Fréchet-jet inverse estimate with four-derivative loss

Adapted from OpenAI/NavierStokesAndEuler at f9e8bc5b38b6e212696e8a30e3e91517af887bbd,
file NavierStokes/SmoothFamilyTorusInverse.lean, under Apache License 2.0.

Changes: use already Lean-verified Z² weight^{-3} summability instead of
the upstream weight^{-4} bound, spend l+3 in coefficient moments rather
than l+4, and propagate the smaller derivative budget unchanged through
the original full-tensor multiplier proof. All source calculations, type
semantics and proof inductive structure otherwise retained.

This is a mathematical CANDIDATE pending exact-head kernel check. No paper
interpretation or Navier–Stokes global conclusion is claimed.
-/

noncomputable section

namespace MathGraph.FullJetFourLoss

open Set Filter MeasureTheory
open NavierStokes
open NavierStokes.TorusInverse
open NavierStokes.SmoothFamilyTorusInverse
open NavierStokes.ParametricTorusInverse (PolynomialGrowth multiplierX multiplierY)
open scoped Topology ContDiff BigOperators

variable {P : Type} [NormedAddCommGroup P] [NormedSpace ℝ P]
  [FiniteDimensional ℝ P]

omit [FiniteDimensional ℝ P] in
theorem coefficient_moment_bound_three {f : Source P} (hf : ContDiff ℝ ∞ f) (hp : Periodic f)
    {S : Set P} (l : ℕ) {C : ℝ} (h : JetBound f S (l + 3) C)
    (p : P) (hps : p ∈ S) :
    coeffSeminorm l (coefficient f p) ≤
      (3 ^ (l + 3) * C) * ∑' k : Frequency, (weight k ^ 3)⁻¹ := by
  apply MathGraph.FourLossBridge.coefficient_seminorm_bound_three
    MathGraph.ThirdLattice.summable_weight_inv_three (slice_smooth hf p) (hp p) l
  · intro x hx y hy
    simpa only [slice, norm_iteratedFDeriv_zero] using h 0 (by omega) p hps (x, y)
  · intro x hx y hy
    rw [← slice_torusXJet hf (l + 3) p]
    exact (norm_torusXJet_le hf (l + 3) (p, (x, y))).trans
      (h (l + 3) le_rfl p hps (x, y))
  · intro x hx y hy
    change ‖SmoothFourierData.xJet (l + 3) (slice (swapTorus f) p) (x, y)‖ ≤ C
    rw [← slice_torusXJet (swapTorus_smooth hf) (l + 3) p]
    apply (norm_torusXJet_le (swapTorus_smooth hf) (l + 3) (p, (x, y))).trans
    rw [norm_jet_swapTorus]
    exact h (l + 3) le_rfl p hps (y, x)

noncomputable def multiplierJetConstantThree : ℕ → ℕ → ℝ
  | 0, l => 3 ^ (l + 3) * ∑' k : Frequency, (weight k ^ 3)⁻¹
  | n + 1, l =>
      (∑ i : BasisIndex P, ‖parameterLift i‖ * ‖(parameterBasis i, (0 : Plane))‖) *
        multiplierJetConstantThree n l +
      (‖torusLiftX (P := P)‖ + ‖torusLiftY (P := P)‖) * ‖omega‖ *
        multiplierJetConstantThree n (l + 1)

theorem multiplierJetConstantThree_nonneg (n l : ℕ) : 0 ≤ multiplierJetConstantThree (P := P) n l := by
  induction n generalizing l with
  | zero =>
      unfold multiplierJetConstantThree
      exact mul_nonneg (by positivity)
        (tsum_nonneg (fun k => inv_nonneg.mpr (pow_nonneg (weight_pos k).le _)))
  | succ n ih =>
      rw [multiplierJetConstantThree]
      exact add_nonneg (mul_nonneg (Finset.sum_nonneg fun i hi => by positivity) (ih l))
        (mul_nonneg (by positivity) (ih (l + 1)))

/-- The loss l+3 comes only from the order-l multiplier and the summable
two-dimensional lattice majorant; it does not grow with jet order. -/
theorem norm_jet_applyMultiplier_le_three (n l : ℕ) {m : Frequency → ℂ}
    {B : ℝ} (hB : 0 ≤ B) (hm : ∀ k, ‖m k‖ ≤ B * weight k ^ l)
    {f : Source P} (hf : ContDiff ℝ ∞ f) (hp : Periodic f)
    {S : Set P} {C : ℝ} (hC : 0 ≤ C) (h : JetBound f S (n + l + 3) C)
    (p : P) (hps : p ∈ S) (Y : Plane) :
    ‖iteratedFDeriv ℝ n (applyMultiplier m f) (p, Y)‖ ≤
      multiplierJetConstantThree (P := P) n l * B * C := by
  have hmg : PolynomialGrowth m := ⟨l, B, hB, hm⟩
  induction n generalizing l m B f C with
  | zero =>
      rw [norm_iteratedFDeriv_zero]
      have ha := SmoothFourierData.rapid_coefficient (slice_smooth hf p) (hp p)
      have hb : coeffSeminorm 0 (fun k => m k * coefficient f p k) ≤
          B * coeffSeminorm l (coefficient f p) := by
        have hb' : ∀ k, ‖m k * coefficient f p k‖ ≤
            B * (weight k ^ l * ‖coefficient f p k‖) := by
          intro k
          rw [norm_mul]
          exact (mul_le_mul_of_nonneg_right (hm k) (norm_nonneg _)).trans_eq (by ring)
        have hh := (multiplied_coeff_rapid hmg hf hp p).summable_norm.tsum_le_tsum hb'
          ((ha l).mul_left B)
        simpa only [coeffSeminorm, pow_zero, one_mul, tsum_mul_left] using hh
      calc
        _ ≤ coeffSeminorm 0 (fun k => m k * coefficient f p k) :=
          norm_series_le (multiplied_coeff_rapid hmg hf hp p) Y
        _ ≤ B * coeffSeminorm l (coefficient f p) := hb
        _ ≤ B * ((3 ^ (l + 3) * C) * ∑' k : Frequency, (weight k ^ 3)⁻¹) :=
          mul_le_mul_of_nonneg_left
            (coefficient_moment_bound_three hf hp l (by simpa only [zero_add] using h) p hps) hB
        _ = _ := by simp only [multiplierJetConstantThree]; ring
  | succ n ih =>
      let G (i : BasisIndex P) : Source P := parameterPartial (parameterBasis i) f
      have hG : ∀ i : BasisIndex P, ContDiff ℝ ∞ (G i) :=
        fun i => parameterPartial_smooth hf _
      have hPG : ∀ i : BasisIndex P, Periodic (G i) :=
        fun i => parameterPartial_periodic hp _
      have hGb : ∀ i : BasisIndex P,
          ‖iteratedFDeriv ℝ n (applyMultiplier m (G i)) (p, Y)‖ ≤
            multiplierJetConstantThree (P := P) n l * B *
              (‖(parameterBasis i, (0 : Plane))‖ * C) := by
        intro i
        refine ih l hB hm (hG i) (hPG i) (mul_nonneg (norm_nonneg _) hC) ?_ hmg
        have hi := h.fixedPartial hf (parameterBasis i, (0 : Plane))
        convert! hi using 1
        omega
      have hmx : ∀ k, ‖multiplierX m k‖ ≤ (‖omega‖ * B) * weight k ^ (l + 1) := by
        intro k
        rw [multiplierX, norm_mul]
        calc
          _ ≤ (‖omega‖ * weight k) * (B * weight k ^ l) :=
            mul_le_mul (norm_freqX_le k) (hm k) (norm_nonneg _)
              (mul_nonneg (norm_nonneg _) (weight_pos k).le)
          _ = _ := by rw [pow_succ]; ring
      have hmy : ∀ k, ‖multiplierY m k‖ ≤ (‖omega‖ * B) * weight k ^ (l + 1) := by
        intro k
        rw [multiplierY, norm_mul]
        calc
          _ ≤ (‖omega‖ * weight k) * (B * weight k ^ l) :=
            mul_le_mul (norm_freqY_le k) (hm k) (norm_nonneg _)
              (mul_nonneg (norm_nonneg _) (weight_pos k).le)
          _ = _ := by rw [pow_succ]; ring
      have hbshift : JetBound f S (n + (l + 1) + 3) C := by
        convert! h using 1
        omega
      have hx := ih (l + 1) (mul_nonneg (norm_nonneg _) hB) hmx hf hp hC hbshift hmg.mulX
      have hy := ih (l + 1) (mul_nonneg (norm_nonneg _) hB) hmy hf hp hC hbshift hmg.mulY
      have hLS (i : BasisIndex P) : ContDiff ℝ ∞
          (fun z : Point P => parameterLift i (applyMultiplier m (G i) z)) :=
        (parameterLift i).contDiff.comp (applyMultiplier_smooth hmg (hG i) (hPG i))
      have hLSum := ContDiff.sum (fun i (_ : i ∈ (Finset.univ : Finset (BasisIndex P))) => hLS i)
      have hLX : ContDiff ℝ ∞
          (fun z : Point P => torusLiftX (P := P) (applyMultiplier (multiplierX m) f z)) :=
        (torusLiftX (P := P)).contDiff.comp (applyMultiplier_smooth hmg.mulX hf hp)
      have hLY : ContDiff ℝ ∞
          (fun z : Point P => torusLiftY (P := P) (applyMultiplier (multiplierY m) f z)) :=
        (torusLiftY (P := P)).contDiff.comp (applyMultiplier_smooth hmg.mulY hf hp)
      have he : fderiv ℝ (applyMultiplier m f) = fun z : Point P =>
          (∑ i : BasisIndex P, parameterLift i (applyMultiplier m (G i) z)) +
          torusLiftX (P := P) (applyMultiplier (multiplierX m) f z) +
          torusLiftY (P := P) (applyMultiplier (multiplierY m) f z) :=
        funext (fderiv_applyMultiplier hmg hf hp)
      rw [← norm_iteratedFDeriv_fderiv, he]
      apply (norm_jet_add (hLSum.add hLX) hLY n (p, Y)).trans
      apply (add_le_add_left (norm_jet_add hLSum hLX n (p, Y)) _).trans
      apply (add_le_add_left (add_le_add_left (norm_jet_sum hLS n (p, Y)) _) _).trans
      calc
        _ ≤ (∑ i : BasisIndex P, ‖parameterLift i‖ *
              (multiplierJetConstantThree (P := P) n l * B *
                (‖(parameterBasis i, (0 : Plane))‖ * C))) +
            ‖torusLiftX (P := P)‖ *
              (multiplierJetConstantThree (P := P) n (l + 1) * (‖omega‖ * B) * C) +
            ‖torusLiftY (P := P)‖ *
              (multiplierJetConstantThree (P := P) n (l + 1) * (‖omega‖ * B) * C) := by
          apply add_le_add
          · apply add_le_add
            · apply Finset.sum_le_sum
              intro i hi
              exact (norm_jet_linear (parameterLift i)
                (applyMultiplier_smooth hmg (hG i) (hPG i)) n (p, Y)).trans
                (mul_le_mul_of_nonneg_left (hGb i) (norm_nonneg _))
            · exact (norm_jet_linear (torusLiftX (P := P))
                (applyMultiplier_smooth hmg.mulX hf hp) n (p, Y)).trans
                (mul_le_mul_of_nonneg_left hx (norm_nonneg _))
          · exact (norm_jet_linear (torusLiftY (P := P))
              (applyMultiplier_smooth hmg.mulY hf hp) n (p, Y)).trans
              (mul_le_mul_of_nonneg_left hy (norm_nonneg _))
        _ = _ := by
          rw [multiplierJetConstantThree]
          have hs : (∑ i : BasisIndex P, ‖parameterLift i‖ *
              (multiplierJetConstantThree (P := P) n l * B *
                (‖(parameterBasis i, (0 : Plane))‖ * C))) =
              (∑ i : BasisIndex P, ‖parameterLift i‖ * ‖(parameterBasis i, (0 : Plane))‖) *
                multiplierJetConstantThree (P := P) n l * B * C := by
            simp only [Finset.sum_mul]
            apply Finset.sum_congr rfl
            intro i hi
            ring
          rw [hs]
          ring

theorem applyMultiplier_finiteJets_three (n l : ℕ) :
    ∃ K : ℝ, 0 ≤ K ∧ ∀ (m : Frequency → ℂ) (B : ℝ), 0 ≤ B →
      (∀ k, ‖m k‖ ≤ B * weight k ^ l) →
      ∀ (f : Source P) (S : Set P) (C : ℝ), ContDiff ℝ ∞ f → Periodic f → 0 ≤ C →
        JetBound f S (n + l + 3) C → JetBound (applyMultiplier m f) S n (K * B * C) := by
  let K := ∑ j ∈ Finset.range (n + 1), multiplierJetConstantThree (P := P) j l
  have hK : 0 ≤ K := Finset.sum_nonneg (fun j hj => multiplierJetConstantThree_nonneg j l)
  refine ⟨K, hK, ?_⟩
  intro m B hB hm f S C hf hp hC h j hj p hps Y
  apply (norm_jet_applyMultiplier_le_three j l hB hm hf hp hC
    (h.mono_order (by omega)) p hps Y).trans
  have hjK : multiplierJetConstantThree (P := P) j l ≤ K :=
    Finset.single_le_sum (fun k hk => multiplierJetConstantThree_nonneg k l)
      (Finset.mem_range.mpr (by omega))
  exact mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_right hjK hB) hC

/-- Uniform full-tensor bound with four torus derivatives lost. The
constant is chosen before the source, parameter set, or input bound. -/
theorem inverse_finiteJets_four (d : Direction) (n : ℕ) :
    ∃ K : ℝ, 0 ≤ K ∧ ∀ (f : Source P) (S : Set P) (C : ℝ),
      ContDiff ℝ ∞ f → Periodic f → 0 ≤ C →
      JetBound f S (n + 4) C → JetBound (inverse d f) S n (K * C) := by
  obtain ⟨K, hK, hb⟩ := applyMultiplier_finiteJets_three (P := P) n 1
  refine ⟨K * (6 * ‖omega⁻¹‖), by positivity, ?_⟩
  intro f S C hf hp hC h
  have hh := hb (multiplier d) (6 * ‖omega⁻¹‖) (by positivity)
    (fun k => by simpa only [pow_one] using norm_multiplier_le d k)
    f S C hf hp hC (by simpa only [Nat.add_assoc] using h)
  exact hh

end MathGraph.FullJetFourLoss

#print axioms MathGraph.FullJetFourLoss.coefficient_moment_bound_three
#print axioms MathGraph.FullJetFourLoss.multiplierJetConstantThree_nonneg
#print axioms MathGraph.FullJetFourLoss.norm_jet_applyMultiplier_le_three
#print axioms MathGraph.FullJetFourLoss.applyMultiplier_finiteJets_three
#print axioms MathGraph.FullJetFourLoss.inverse_finiteJets_four
