import NavierStokes.R3.WholeSpaceComparisonClosure

/-!
# V10: precise scalar-envelope obstruction for pressure-flux (10.19)

The source envelope below represents the *reported scalar structure* of
the original manuscript equation (10.19): (B+1)/R times
(B^(1/2) + R^(-3/4)*B^(3/4)). This interpretation needs independently
approved source mathematical signoff. The Lean envelope is the ACTUAL
NavierStokesR3.WholeSpaceComparisonClosure.pressureEnvelope of upstream
OpenAI/NavierStokesAndEuler@f9e8bc5b38b6e212696e8a30e3e91517af887bbd.

The scope is scalar ordering only: the existence of abstract values
A,B,R does NOT assert existence of a Navier-Stokes PDE solution realizing
them, does NOT refute the original manuscript pressure-flux estimate, and
does NOT prevent a different independent proof of that estimate.

It proves the existing verified upper bound does not imply the
manuscript-style upper bound by pure numerical comparison, even under
a one-way Sobolev relation B <= S*(A + M/R).
-/

noncomputable section
namespace MathGraph.PressureEnvelopeObstruction

open NavierStokesR3.WholeSpaceComparisonClosure
open scoped ENNReal Topology

def sourceEnvelope (R B : ℝ) : ℝ :=
  ((B + 1) / R) *
    (B ^ (1 / 2 : ℝ) + R ^ (-(3 / 4 : ℝ)) * B ^ (3 / 4 : ℝ))

def formalEnvelope (R A B : ℝ) : ℝ :=
  pressureEnvelope R A B

/-- Positive check against the source-formula convention. -/
theorem source_at_unit : sourceEnvelope 1 1 = 4 := by
  norm_num [sourceEnvelope]

/-- Exact evaluation of the genuine OpenAI Lean pressure bound at R=B=1. -/
theorem formal_at_unit (A : ℝ) : formalEnvelope 1 A 1 = 2 * A + 3 := by
  simp [formalEnvelope, pressureEnvelope]
  ring

/-- The abstract source formula cannot be recovered by a uniform numerical
    domination of the original Lean envelope without controlling A. -/
theorem no_uniform_envelope_transfer :
    ¬ ∃ C : ℝ, 0 ≤ C ∧ ∀ R A B : ℝ,
      1 ≤ R → 0 ≤ A → 0 ≤ B →
      formalEnvelope R A B ≤ C * sourceEnvelope R B := by
  rintro ⟨C, hC, hbound⟩
  have hA : (0 : ℝ) ≤ 2 * C + 1 := by linarith
  have h := hbound 1 (2 * C + 1) 1 (by norm_num) hA (by norm_num)
  rw [formal_at_unit, source_at_unit] at h
  nlinarith

/-- The one-way weighted Sobolev relation B <= S*(A + M/R) is not a
    missing upper bound on A. The impossibility remains under any
    positive fixed S and any nonnegative M. This models exactly the
    direction issue, NOT the complete analytic premises of a PDE solution. -/
theorem no_transfer_from_one_way_sobolev
    (S M : ℝ) (hS : 0 < S) (hM : 0 ≤ M) :
    ¬ ∃ C : ℝ, 0 ≤ C ∧ ∀ R A B : ℝ,
      1 ≤ R → 0 ≤ A → 0 ≤ B →
      B ≤ S * (A + M / R) →
      formalEnvelope R A B ≤ C * sourceEnvelope R B := by
  rintro ⟨C, hC, hbound⟩
  let A : ℝ := 2 * C + 1 + S⁻¹
  have hSinv : 0 < S⁻¹ := inv_pos.mpr hS
  have hA : 0 ≤ A := by
    dsimp [A]
    positivity
  have hSM : 0 ≤ S * (2 * C + 1 + M) :=
    mul_nonneg hS.le (by linarith)
  have hSinvMul : S * S⁻¹ = 1 := mul_inv_cancel₀ hS.ne'
  have hSob : (1 : ℝ) ≤ S * (A + M / 1) := by
    dsimp [A]
    norm_num only [div_one]
    nlinarith
  have h := hbound 1 A 1 (by norm_num) hA (by norm_num) hSob
  rw [formal_at_unit, source_at_unit] at h
  dsimp [A] at h
  nlinarith

end MathGraph.PressureEnvelopeObstruction

#print axioms MathGraph.PressureEnvelopeObstruction.source_at_unit
#print axioms MathGraph.PressureEnvelopeObstruction.formal_at_unit
#print axioms MathGraph.PressureEnvelopeObstruction.no_uniform_envelope_transfer
#print axioms MathGraph.PressureEnvelopeObstruction.no_transfer_from_one_way_sobolev
