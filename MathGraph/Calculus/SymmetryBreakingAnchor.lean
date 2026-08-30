import MathGraph.Calculus.VerifierBoundaryEndogenization

namespace MathGraph.Calculus

/-- On the two-point deciding witness, a single distinguished endpoint is the
weakest possible oriented external datum: the opposite endpoint is generated
by the unique nontrivial carrier automorphism. -/
def Stage29TaskFromAnchor (a : Bool) : Stage26TaskBoundary Bool :=
  ⟨a, Bool.not a⟩

/-- The previously used forward verifier task is reconstructible from one
external anchor bit. -/
theorem stage29_false_anchor_recovers_forward_task :
    Stage29TaskFromAnchor false = Stage28BoolTask := by
  rfl

/-- Flipping the anchor flips the operational task. -/
theorem stage29_true_anchor_recovers_reverse_task :
    Stage29TaskFromAnchor true = (⟨true, false⟩ : Stage26TaskBoundary Bool) := by
  rfl

/-- Fixing a residual source as the external anchor removes the final ambiguity
from Stage 20 without supplying a target field. -/
def AnchoredGenerator
    {ι Ω : Type} (G : Ω → Ω → Type) (P : ProbeFamily ι Ω) (anchor : Ω) :
    Ω → Ω → Type :=
  fun x y =>
    { r : ProbeResidual G P anchor x y // ProbeObservation G anchor x }

/-- The `false` anchor licenses the forward edge in the symmetric cold seed. -/
theorem stage29_false_anchor_generates_forward :
    Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) false false true) := by
  refine ⟨⟨stage19_cold_generic_residual, ?_⟩⟩
  exact ⟨(.nil : FreePath Stage13G0 false false)⟩

/-- The same fixed anchor does not license the reverse edge.  The residual is
symmetric, but the positive reachability witness is not. -/
theorem stage29_false_anchor_excludes_reverse :
    ¬ Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) false true false) := by
  intro h
  rcases h with ⟨⟨_r, hReach⟩⟩
  rcases hReach with ⟨p⟩
  exact (emptyGenerator_no_false_to_true p).elim

/-- Conversely, the `true` anchor selects exactly the reverse direction. -/
theorem stage29_true_anchor_generates_reverse :
    Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) true true false) := by
  refine ⟨⟨stage21_cold_true_generic_residual, ?_⟩⟩
  exact ⟨(.nil : FreePath Stage13G0 true true)⟩

/-- A fully endogenous anchor in the symmetric Bool seed would have to be fixed
by the seed's nontrivial renaming automorphism.  No Bool point is fixed by
negation. -/
structure Stage29CanonicalAnchor where
  anchor : Bool
  rename_invariant : Bool.not anchor = anchor

/-- Exact symmetry obstruction for eliminating the last external bit. -/
theorem stage29_no_endogenous_canonical_anchor :
    ¬ Nonempty Stage29CanonicalAnchor := by
  intro h
  rcases h with ⟨a⟩
  have hInv := a.rename_invariant
  cases hAnchor : a.anchor <;> simp [hAnchor] at hInv

/-- The anchor carries precisely the symmetry-breaking role: once erased, the
old symmetric residual mechanism again licenses both directions and admits no
canonical orientation. -/
theorem stage29_anchor_ablation_restores_symmetry_boundary :
    (Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
     Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
    ¬ Nonempty Stage21CanonicalOrientation :=
  stage26_orientation_ablation_restores_stage21_boundary

/-- Stage-29 minimal-external-contact certificate.

For the two-point symmetric deciding seed, the ordered source-target verifier
request is stronger than necessary: one distinguished endpoint reconstructs
the ordered task and uniquely selects the corresponding residual-derived edge.
Flipping that one bit flips the selected direction.  But the bit itself cannot
be generated canonically from the symmetric seed while respecting its
nontrivial renaming.  Thus the remaining exogenous content is not an ordered
pair; it is one symmetry-breaking bit of contact. -/
theorem symmetry_breaking_anchor_certificate :
    Stage29TaskFromAnchor false = Stage28BoolTask ∧
    Stage29TaskFromAnchor true = (⟨true, false⟩ : Stage26TaskBoundary Bool) ∧
    Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) false false true) ∧
    (¬ Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) false true false)) ∧
    Nonempty (AnchoredGenerator Stage13G0 (NoProbes Bool) true true false) ∧
    (¬ Nonempty Stage29CanonicalAnchor) ∧
    ((Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
      Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
     ¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage29_false_anchor_recovers_forward_task,
    stage29_true_anchor_recovers_reverse_task,
    stage29_false_anchor_generates_forward,
    stage29_false_anchor_excludes_reverse,
    stage29_true_anchor_generates_reverse,
    stage29_no_endogenous_canonical_anchor,
    stage29_anchor_ablation_restores_symmetry_boundary⟩

end MathGraph.Calculus
