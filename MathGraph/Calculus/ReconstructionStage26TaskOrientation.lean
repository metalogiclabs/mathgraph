import MathGraph.Calculus.ReconstructionStage25StateNecessity

namespace MathGraph.Calculus

/-- An ordered task boundary is external oriented evidence: it says which
endpoint is the current source and which is the requested target.  It is not a
new internal observation or generator primitive. -/
structure Stage26TaskBoundary (Ω : Type) where
  source : Ω
  target : Ω

/-- A raw developmental edge is admissible for a task exactly when its
endpoints match the ordered external request. -/
def Stage26TaskAdmissible {Ω : Type}
    (T : Stage26TaskBoundary Ω) (x y : Ω) : Prop :=
  x = T.source ∧ y = T.target

/-- The internal residual mechanism is unchanged.  The external task boundary
merely restricts which already-licensed directed edge is acted upon. -/
def Stage26TaskGenerator
    {ι Ω : Type} (G : Ω → Ω → Type) (P : ProbeFamily ι Ω)
    (T : Stage26TaskBoundary Ω) : Type :=
  Stage20Generator G P T.source T.target

/-- In the cold Bool world an ordered external request `false -> true` selects
the forward developmental edge that the residual calculus already licenses. -/
theorem stage26_forward_task_is_licensed :
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨false, true⟩) := by
  exact stage21_cold_stage20_generates_both_directions.1

/-- Reversing the external request reverses the selected edge, again without
changing the internal residual calculus. -/
theorem stage26_reverse_task_is_licensed :
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨true, false⟩) := by
  exact stage21_cold_stage20_generates_both_directions.2

/-- Once the ordered task boundary is present, the reverse edge is not
admissible for the forward request.  The symmetry is broken by the request,
not by adding an orientation primitive to the calculus. -/
theorem stage26_forward_task_excludes_reverse_admissibility :
    ¬ Stage26TaskAdmissible (⟨false, true⟩ : Stage26TaskBoundary Bool)
      true false := by
  simp [Stage26TaskAdmissible]

/-- Likewise, the forward edge is not admissible under the reversed request. -/
theorem stage26_reverse_task_excludes_forward_admissibility :
    ¬ Stage26TaskAdmissible (⟨true, false⟩ : Stage26TaskBoundary Bool)
      false true := by
  simp [Stage26TaskAdmissible]

/-- The task orientation itself is equivariant under renaming of the carrier:
renaming both ordered endpoints by Bool negation turns the forward task into
the reverse task.  No hidden distinguished Bool value is used. -/
theorem stage26_task_orientation_rename_equivariant :
    (Stage26TaskBoundary.mk (Bool.not false) (Bool.not true) :
      Stage26TaskBoundary Bool) = ⟨true, false⟩ := by
  rfl

/-- Exact orientation ablation recovers the Stage-21 obstruction: if the
ordered task boundary is removed, the cold residual mechanism again licenses
both endpoint directions and no canonical symmetric/equivariant chooser
exists. -/
theorem stage26_orientation_ablation_restores_stage21_boundary :
    (Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
     Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
    ¬ Nonempty Stage21CanonicalOrientation := by
  exact ⟨stage21_cold_stage20_generates_both_directions,
    stage21_no_canonical_orientation_from_symmetric_pair⟩

/-- Stage-26 certificate: unique operational direction need not be an internal
primitive of the minimal calculus.  Bare residual evidence remains symmetric
(Stage 21); an ordered external task/verifier request supplies exactly the
symmetry-breaking evidence needed to select one already-licensed direction,
renames equivariantly, and its ablation restores the bidirectional/canonical-
choice obstruction. -/
theorem reconstruction_stage26_task_orientation_certificate :
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨false, true⟩) ∧
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨true, false⟩) ∧
    (¬ Stage26TaskAdmissible (⟨false, true⟩ : Stage26TaskBoundary Bool)
      true false) ∧
    (¬ Stage26TaskAdmissible (⟨true, false⟩ : Stage26TaskBoundary Bool)
      false true) ∧
    ((Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
      Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
     ¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage26_forward_task_is_licensed,
    stage26_reverse_task_is_licensed,
    stage26_forward_task_excludes_reverse_admissibility,
    stage26_reverse_task_excludes_forward_admissibility,
    stage26_orientation_ablation_restores_stage21_boundary⟩

end MathGraph.Calculus
