import MathGraph.Calculus.ReconstructionStage17DirectGeneratorGenesis

namespace MathGraph.Calculus

/-- Stage 18 removes the remaining Stage-17 target-directed compiler rule.
The new raw generator evidence is the oriented residual gap itself: a selected
source reaches the left endpoint, fails to reach the right endpoint, and the
current interface still identifies those endpoints. No protected target is
passed to a separate constructor or interpreter. -/
structure Stage18ResidualEdge
    {Ω : Type} (G : Ω → Ω → Type) (B selected : List Ω) (x y : Ω) where
  source : Ω
  selected_source : source ∈ selected
  indistinguishable : ListProbeEq G B x y
  reaches_left : Nonempty (FreePath G source x)
  misses_right : ¬ Nonempty (FreePath G source y)

/-- The residual witness type is used directly as the raw generator relation.
There is no intermediate schema object and no `source + target ↦ edge` rule. -/
def Stage18Generator
    {Ω : Type} (G : Ω → Ω → Type) (B selected : List Ω) :
    Ω → Ω → Type :=
  fun x y => Stage18ResidualEdge G B selected x y

/-- With no selected residual source, no nontrivial residual-edge evidence can
exist, hence free continuation cannot manufacture `false → true`. -/
theorem stage18_empty_selection_has_no_cross :
    ¬ Nonempty (FreePath (Stage18Generator Stage13G0 [] []) false true) := by
  intro h
  rcases h with ⟨p⟩
  cases p with
  | step e rest =>
      exact (by simpa using e.selected_source)

/-- The endogenous Stage-13 selection supplies exactly the source needed for
an oriented residual witness. The witness itself is now a primitive raw edge;
no protected target argument or schema compilation occurs. -/
theorem stage18_residual_itself_generates_cross :
    Nonempty
      (FreePath
        (Stage18Generator Stage13G0 []
          (finiteResidualSelect Stage13G0 Stage13Candidates []))
        false true) := by
  rw [stage13_selection_is_endogenous]
  refine ⟨FreePath.ofGenerator ?_⟩
  refine
    { source := false
      selected_source := by simp
      indistinguishable := ?_
      reaches_left := ?_
      misses_right := ?_ }
  · intro k hk
    exact nomatch hk
  · exact ⟨(.nil : FreePath Stage13G0 false false)⟩
  · intro h
    rcases h with ⟨p⟩
    exact (emptyGenerator_no_false_to_true p).elim

/-- Exact selection ablation deletes the raw evidence again. -/
theorem stage18_exact_selection_ablation_restores_failure :
    (¬ Nonempty (FreePath (Stage18Generator Stage13G0 [] []) false true)) ∧
    Nonempty
      (FreePath
        (Stage18Generator Stage13G0 []
          (finiteResidualSelect Stage13G0 Stage13Candidates []))
        false true) :=
  ⟨stage18_empty_selection_has_no_cross,
   stage18_residual_itself_generates_cross⟩

/-- Any putative edge under an empty selected interface is impossible directly
from its own evidence field. -/
theorem stage18_no_selected_no_generator_evidence
    {Ω : Type} (G : Ω → Ω → Type) (B : List Ω) (x y : Ω) :
    Stage18Generator G B [] x y → Empty := by
  intro e
  exact (by simpa using e.selected_source)

/-- Stage-18 residual-as-generator certificate.

The remaining Stage-17 meta-rule has been removed from the developmental path:
* no protected target is supplied;
* no constructor schema is formed;
* no separate function interprets `(selected source, target)` as `Unit`;
* instead, an oriented verified residual gap is itself the Type-valued raw
  generator evidence between the endpoints it separates;
* free closure consumes that evidence unchanged;
* exact selected-source ablation removes the new continuation.

This does not eliminate the universal notion of a typed residual witness or
free continuation. It establishes the stronger identification that verified
residual evidence can inhabit the raw generator layer directly, without a
fixed domain-specific promotion compiler. -/
theorem reconstruction_stage18_residual_as_generator_certificate :
    (¬ Nonempty (FreePath (Stage18Generator Stage13G0 [] []) false true)) ∧
    Nonempty
      (FreePath
        (Stage18Generator Stage13G0 []
          (finiteResidualSelect Stage13G0 Stage13Candidates []))
        false true) :=
  stage18_exact_selection_ablation_restores_failure

end MathGraph.Calculus
