import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# HTilt Coordinate Checklist Core

Reusable Lean core for the finite pre-spectral coordinate checklist theorem.

This module treats coordinates only as finite real pairs `(u,v)`. It does not
prove that any coordinate is an eigenvalue or that a coordinate list is a matrix
spectrum.
-/

namespace HTilt.CoordinateChecklist

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

/-- Projection: the checklist contains the residual envelope. -/
theorem checklist_residual_envelope
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    ResidualEnvelope a b B coords := by
  exact checklist.1

/-- Projection: the checklist contains the positive-gap envelope. -/
theorem checklist_positive_gap_envelope
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    PositiveGapEnvelope a δ coords := by
  exact checklist.2.1

/-- Projection: the checklist contains positivity of `δ`. -/
theorem checklist_delta_pos
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    0 < δ := by
  exact checklist.2.2.1

/-- Projection: the checklist contains nonnegativity of `c`. -/
theorem checklist_c_nonneg
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    0 ≤ c := by
  exact checklist.2.2.2.1

/-- Projection: the checklist contains the explicit scalar shift bound. -/
theorem checklist_explicit_c_bound
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    B / (2 * δ) < c := by
  exact checklist.2.2.2.2

/-- The residual envelope is vacuous for the empty coordinate list. -/
theorem nil_residual_envelope
    (a b B : ℝ) :
    ResidualEnvelope a b B [] := by
  intro p hp
  simp at hp

/-- The positive-gap envelope is vacuous for the empty coordinate list. -/
theorem nil_positive_gap_envelope
    (a δ : ℝ) :
    PositiveGapEnvelope a δ [] := by
  intro p hp
  simp at hp

/-- Nil/base constructor for the bundled coordinate-envelope checklist. -/
theorem nil_coordinate_envelope_checklist
    (c a b B δ : ℝ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ [] := by
  constructor
  · exact nil_residual_envelope a b B
  constructor
  · exact nil_positive_gap_envelope a δ
  constructor
  · exact delta_pos
  constructor
  · exact c_nonneg
  · exact c_bound

/-- A pointwise residual bound builds the residual envelope for `[p]`. -/
theorem singleton_residual_envelope
    (a b B : ℝ)
    (p : Coord)
    (hres : residual a b p ≤ B) :
    ResidualEnvelope a b B [p] := by
  intro q hq
  simp at hq
  subst hq
  exact hres

/-- A pointwise positive-gap bound builds the positive-gap envelope for `[p]`. -/
theorem singleton_positive_gap_envelope
    (a δ : ℝ)
    (p : Coord)
    (hgap : δ ≤ a - p.1) :
    PositiveGapEnvelope a δ [p] := by
  intro q hq
  simp at hq
  subst hq
  exact hgap

/-- Constructor: pointwise singleton evidence builds the bundled checklist. -/
theorem singleton_coordinate_envelope_checklist
    (c a b B δ : ℝ)
    (p : Coord)
    (hres : residual a b p ≤ B)
    (hgap : δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ [p] := by
  constructor
  · exact singleton_residual_envelope a b B p hres
  constructor
  · exact singleton_positive_gap_envelope a δ p hgap
  constructor
  · exact delta_pos
  constructor
  · exact c_nonneg
  · exact c_bound

/-- Cons constructor for the residual envelope. -/
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

/-- Cons constructor for the positive-gap envelope. -/
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

/-- Cons constructor for the bundled coordinate-envelope checklist. -/
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

/-- A pointwise residual proof over a finite list is exactly a residual envelope. -/
theorem pointwise_residual_envelope
    (a b B : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B) :
    ResidualEnvelope a b B coords := by
  exact hres

/-- A pointwise gap proof over a finite list is exactly a positive-gap envelope. -/
theorem pointwise_positive_gap_envelope
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1) :
    PositiveGapEnvelope a δ coords := by
  exact hgap

/-- Finite-list checklist builder. -/
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

/--
Master pre-spectral coordinate theorem.

Pointwise finite-list evidence plus the explicit scalar side conditions imply
shifted dominance for every coordinate in the list.
-/
theorem finite_coordinate_shifted_dominance_master
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres : ∀ p ∈ coords, residual a b p ≤ B)
    (hgap : ∀ p ∈ coords, δ ≤ a - p.1)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact shiftedSqMod_gt_for_all_coords_of_explicit_c_envelopes
    c a b B δ coords delta_pos c_nonneg c_bound hres hgap

/--
Checklist form of the master theorem.

A bundled coordinate-envelope checklist implies the same shifted dominance.
-/
theorem finite_coordinate_shifted_dominance_from_checklist
    (c a b B δ : ℝ)
    (coords : List Coord)
    (checklist : CoordinateEnvelopeChecklist c a b B δ coords) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  rcases checklist with ⟨hres, hgap, delta_pos, c_nonneg, c_bound⟩
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords hres hgap delta_pos c_nonneg c_bound


/-- Raw modulus-square residual evidence builds the residual envelope. -/
theorem raw_modsq_residual_builds_residual_envelope
    (a b B : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B) :
    ResidualEnvelope a b B coords := by
  intro p hp
  unfold residual
  exact hres p hp

/-- Raw strict real-part gap evidence builds the positive-gap envelope. -/
theorem raw_strict_gap_builds_positive_gap_envelope
    (a δ : ℝ)
    (coords : List Coord)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ) :
    PositiveGapEnvelope a δ coords := by
  intro p hp
  have h := hgap p hp
  linarith

/-- Raw external evidence builds the bundled coordinate checklist. -/
theorem coordinate_envelope_checklist_from_raw_evidence
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    CoordinateEnvelopeChecklist c a b B δ coords := by
  exact list_coordinate_envelope_checklist
    c a b B δ coords
    (raw_modsq_residual_builds_residual_envelope a b B coords hres)
    (raw_strict_gap_builds_positive_gap_envelope a δ coords hgap)
    delta_pos c_nonneg c_bound

/-- Raw external finite-coordinate evidence implies shifted dominance. -/
theorem finite_coordinate_shifted_dominance_from_raw_evidence
    (c a b B δ : ℝ)
    (coords : List Coord)
    (hres :
      ∀ p ∈ coords,
        |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B)
    (hgap : ∀ p ∈ coords, p.1 ≤ a - δ)
    (delta_pos : 0 < δ)
    (c_nonneg : 0 ≤ c)
    (c_bound : B / (2 * δ) < c) :
    ∀ p ∈ coords,
      shiftedSqMod c p.1 p.2 < shiftedSqMod c a b := by
  exact finite_coordinate_shifted_dominance_master
    c a b B δ coords
    (raw_modsq_residual_builds_residual_envelope a b B coords hres)
    (raw_strict_gap_builds_positive_gap_envelope a δ coords hgap)
    delta_pos c_nonneg c_bound


/-- A reusable certificate bundling raw finite-coordinate dominance evidence. -/
structure RawCoordinateDominanceCertificate where
  c : ℝ
  a : ℝ
  b : ℝ
  B : ℝ
  δ : ℝ
  coords : List Coord
  rawResidual :
    ∀ p ∈ coords,
      |(p.1^2 + p.2^2) - (a^2 + b^2)| ≤ B
  rawGap :
    ∀ p ∈ coords, p.1 ≤ a - δ
  delta_pos : 0 < δ
  c_nonneg : 0 ≤ c
  c_bound : B / (2 * δ) < c

/-- A raw coordinate dominance certificate builds the checklist. -/
theorem RawCoordinateDominanceCertificate.to_checklist
    (cert : RawCoordinateDominanceCertificate) :
    CoordinateEnvelopeChecklist cert.c cert.a cert.b cert.B cert.δ cert.coords := by
  exact coordinate_envelope_checklist_from_raw_evidence
    cert.c cert.a cert.b cert.B cert.δ cert.coords
    cert.rawResidual cert.rawGap cert.delta_pos cert.c_nonneg cert.c_bound

/-- A raw certificate implies shifted dominance over its finite list. -/
theorem RawCoordinateDominanceCertificate.shifted_dominance
    (cert : RawCoordinateDominanceCertificate) :
    ∀ p ∈ cert.coords,
      shiftedSqMod cert.c p.1 p.2 < shiftedSqMod cert.c cert.a cert.b := by
  exact finite_coordinate_shifted_dominance_from_raw_evidence
    cert.c cert.a cert.b cert.B cert.δ cert.coords
    cert.rawResidual cert.rawGap cert.delta_pos cert.c_nonneg cert.c_bound

end HTilt.CoordinateChecklist
