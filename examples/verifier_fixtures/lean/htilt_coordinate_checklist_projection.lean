import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic

/-!
# Finite H-Tilt Coordinate Checklist Projection

This fixture proves projection lemmas for the bundled pre-spectral coordinate
checklist.

It treats coordinates only as finite real pairs `(u,v)`. It does not prove that
the coordinate list is a matrix spectrum.

No matrices, eigenvalues, spectral theorem, Perron--Frobenius, irreducibility,
or convergence claims are made.
-/

namespace HTiltCoordinateChecklistProjection

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

end HTiltCoordinateChecklistProjection
