import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Finite H-Tilt Coordinate List Checklist Builder

This fixture proves the finite-list builder for the pre-spectral coordinate
checklist.

It treats coordinates only as finite real pairs `(u,v)`. It does not prove that
the coordinate list is a matrix spectrum.

If every coordinate in a finite list satisfies the pointwise residual and
positive-gap bounds, and the scalar side conditions hold, then Lean constructs
the bundled `CoordinateEnvelopeChecklist` for the whole list. The checklist then
implies shifted squared-modulus dominance for every coordinate in the list.

No matrices, eigenvalues, spectral theorem, Perron--Frobenius, irreducibility,
or convergence claims are made.
-/

namespace HTiltCoordinateListChecklistBuilder

/-- A coordinate pair representing the real and imaginary parts of a mode. -/
abbrev Coord := ℝ × ℝ

/-- Squared modulus of `(c + a) + ib`, represented over reals. -/
def shiftedSqMod (c a b : ℝ) : ℝ :=
  (c + a)^2 + b^2

/-- The unshifted squared-modulus residual of a competitor coordinate. -/
def residual (a b : ℝ) (p : Coord) : ℝ :=
  |(p.1^2 + p.2^2) - (a^2 + b^2)|

/-- `B` is a residual envelope for all coordinates in the finite list. -/
def ResidualEnvelope (a b B : ℝ) (coords : List Coord) : Prop :=
  ∀ p ∈ coords, residual a b p ≤ B

/-- `δ` is a lower bound on the target real-part gap against all coordinates. -/
def PositiveGapEnvelope (a δ : ℝ) (coords : List Coord) : Prop :=
  ∀ p ∈ coords, δ ≤ a - p.1

/--
A pre-spectral coordinate dominance checklist.

This is only a finite-coordinate certificate. It does not say that the
coordinates came from a matrix spectrum.
-/
def CoordinateEnvelopeChecklist
    (c a b B δ : ℝ)
    (coords : List Coord) : Prop :=
  ResidualEnvelope a b B coords ∧
  PositiveGapEnvelope a δ coords ∧
  0 < δ ∧
  0 ≤ c ∧
  B / (2 * δ) < c

/--
A pointwise residual proof over a finite list is exactly a residual envelope.
-/
theorem pointwise_residual_envelope
    (a b B : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B) :
    ResidualEnvelope a b B coords := by
  exact hres

/--
A pointwise gap proof over a finite list is exactly a positive-gap envelope.
-/
theorem pointwise_positive_gap_envelope
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1) :
    PositiveGapEnvelope a δ coords := by
  exact hgap

/--
Finite-list checklist builder.

Pointwise residual evidence, pointwise positive-gap evidence, and scalar side
conditions construct the bundled checklist for the whole finite coordinate list.
-/
theorem list_coordinate_envelope_checklist
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ coords := by
  constructor
  · exact pointwise_residual_envelope a b B coords hres
  constructor
  · exact pointwise_positive_gap_envelope a δ coords hgap
  constructor
  · exact delta_pos
  constructor
  · exact c_nonneg
  · exact c_bound

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

/-- Coordinate-envelope dominance from the abstract scalar shift condition. -/
theorem shiftedSqMod_gt_for_all_coords_of_envelopes
    (c a b B δ : ℝ)
    (coords : List Coord)
    (c_nonneg : 0 ≤ c)
    (residual_envelope : ResidualEnvelope a b B coords)
    (gap_envelope : PositiveGapEnvelope a δ coords)
    (shift_bound : B < 2 * c * δ) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  intro p hp
  apply shiftedSqMod_gt_of_bound
  have hle_gap : 2 * c * δ ≤ 2 * c * (a - p.1) := by
    nlinarith [c_nonneg, gap_envelope p hp]
  exact lt_of_le_of_lt (residual_envelope p hp) (lt_of_lt_of_le shift_bound hle_gap)

/-- Coordinate-envelope dominance from the explicit computable shift rule. -/
theorem shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes
    (c a b B δ : ℝ)
    (coords : List Coord)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c)
    (residual_envelope : ResidualEnvelope a b B coords)
    (gap_envelope : PositiveGapEnvelope a δ coords) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  apply shiftedSqMod_gt_for_all_coords_of_envelopes
  · exact c_nonneg
  · exact residual_envelope
  · exact gap_envelope
  · have hden_pos : 0 < 2 * δ := by
      nlinarith
    have hmul : B < c * (2 * δ) := by
      exact (div_lt_iff₀ hden_pos).mp c_bound
    nlinarith

/-- A bundled checklist implies shifted dominance for every coordinate. -/
theorem shiftedSqMod_gt_for_all_coords_of_checklist
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  rcases checklist with ⟨residual_envelope, gap_envelope, delta_pos, c_nonneg, c_bound⟩
  exact shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes
    c a b B δ coords delta_pos c_nonneg c_bound residual_envelope gap_envelope

/--
Finite-list builder-to-dominance theorem.

Pointwise finite-list evidence constructs the checklist and therefore gives
shifted dominance for every coordinate in the list.
-/
theorem shiftedSqMod_gt_for_all_coords_of_list_checklist_evidence
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  have checklist : CoordinateEnvelopeChecklist c a b B δ coords :=
    list_coordinate_envelope_checklist c a b B δ coords
      hres hgap delta_pos c_nonneg c_bound
  exact shiftedSqMod_gt_for_all_coords_of_checklist c a b B δ coords checklist

end HTiltCoordinateListChecklistBuilder
