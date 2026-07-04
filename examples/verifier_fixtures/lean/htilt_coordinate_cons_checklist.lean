import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Finite H-Tilt Coordinate Cons Checklist

This fixture proves the cons-constructor layer for the pre-spectral coordinate
checklist.

It treats coordinates only as finite real pairs `(u,v)`. It does not prove that
the coordinate list is a matrix spectrum.

If a coordinate list already has a `CoordinateEnvelopeChecklist`, and a new head
coordinate `p` satisfies the same pointwise residual and positive-gap bounds,
then the extended list `p :: coords` also has a checklist.

No matrices, eigenvalues, spectral theorem, Perron--Frobenius, irreducibility,
or convergence claims are made.
-/

namespace HTiltCoordinateConsChecklist

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
Cons constructor for the residual envelope.

If `coords` has a residual envelope and the new head coordinate satisfies the
same residual bound, then `p :: coords` has the residual envelope.
-/
theorem cons_residual_envelope
    (a b B : ℝ)
    (p : Coord)
    (coords : List Coord)
    (hres_head : residual a b p ≤ B)
    (hres_tail : ResidualEnvelope a b B coords) :
    ResidualEnvelope a b B (p :: coords) := by
  intro q hq
  simp at hq
  rcases hq with hq | hq
  · subst hq
    exact hres_head
  · exact hres_tail q hq

/--
Cons constructor for the positive-gap envelope.

If `coords` has a positive-gap envelope and the new head coordinate satisfies
the same gap bound, then `p :: coords` has the positive-gap envelope.
-/
theorem cons_positive_gap_envelope
    (a δ : ℝ)
    (p : Coord)
    (coords : List Coord)
    (hgap_head : δ ≤ a - p.1)
    (hgap_tail : PositiveGapEnvelope a δ coords) :
    PositiveGapEnvelope a δ (p :: coords) := by
  intro q hq
  simp at hq
  rcases hq with hq | hq
  · subst hq
    exact hgap_head
  · exact hgap_tail q hq

/--
Cons constructor for the bundled coordinate-envelope checklist.

Given a checklist for `coords`, plus pointwise residual and gap evidence for a
new head coordinate `p`, construct a checklist for `p :: coords`.
-/
theorem cons_coordinate_envelope_checklist
    (c a b B δ : ℝ)
    (p : Coord)
    (coords : List Coord)
    (checklist_tail : CoordinateEnvelopeChecklist c a b B δ coords)
    (hres_head : residual a b p ≤ B)
    (hgap_head : δ ≤ a - p.1) :
    CoordinateEnvelopeChecklist c a b B δ (p :: coords) := by
  rcases checklist_tail with ⟨hres_tail, hgap_tail, delta_pos, c_nonneg, c_bound⟩
  constructor
  · exact cons_residual_envelope a b B p coords hres_head hres_tail
  constructor
  · exact cons_positive_gap_envelope a δ p coords hgap_head hgap_tail
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
Cons constructor-to-dominance theorem.

If the tail already has a checklist and the head coordinate satisfies the same
pointwise bounds, the extended list has shifted dominance for every coordinate.
-/
theorem shiftedSqMod_gt_for_all_coords_of_cons_checklist_evidence
    (c a b B δ : ℝ)
    (p : Coord)
    (coords : List Coord)
    (checklist_tail : CoordinateEnvelopeChecklist c a b B δ coords)
    (hres_head : residual a b p ≤ B)
    (hgap_head : δ ≤ a - p.1) :
    ∀ q ∈ p :: coords,
      shiftedSqMod c q.1 q.2 < shiftedSqMod c a b := by
  have checklist_cons : CoordinateEnvelopeChecklist c a b B δ (p :: coords) :=
    cons_coordinate_envelope_checklist c a b B δ p coords
      checklist_tail hres_head hgap_head
  exact shiftedSqMod_gt_for_all_coords_of_checklist c a b B δ (p :: coords) checklist_cons

end HTiltCoordinateConsChecklist
