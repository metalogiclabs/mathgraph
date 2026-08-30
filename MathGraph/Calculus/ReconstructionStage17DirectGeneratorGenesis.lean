import MathGraph.Calculus.ReconstructionStage16SchemaGenesis

namespace MathGraph.Calculus

/-- Stage 17 removes the Stage-16 intermediate schema object entirely. A
verified residual is compiled directly into raw directed generator evidence.
No constructor-schema datatype or schema-language membership is used. -/
def Stage17SynthesizeGenerator (newSources : List Bool) (target : Bool) :
    Bool → Bool → Type :=
  fun x y => if x ∈ newSources ∧ y = target then Unit else Empty

/-- The cold developmental state has no newly selected residual sources, hence
its directly synthesized generator contains no cross-endpoint evidence. -/
theorem stage17_empty_residual_generator_has_no_cross :
    ¬ Nonempty (FreePath (Stage17SynthesizeGenerator [] true) false true) := by
  intro h
  rcases h with ⟨p⟩
  induction p with
  | nil => contradiction
  | @cons a b c g rest ih =>
      simp [Stage17SynthesizeGenerator] at g

/-- The existing residual selector supplies the source data. Direct generator
synthesis immediately creates the missing raw continuation, without first
forming a schema value and then compiling it. -/
theorem stage17_residual_directly_generates_cross :
    Nonempty
      (FreePath
        (Stage17SynthesizeGenerator
          (finiteResidualSelect Stage13G0 Stage13Candidates []) true)
        false true) := by
  rw [stage13_selection_is_endogenous]
  refine ⟨FreePath.ofGenerator ?_⟩
  simp [Stage17SynthesizeGenerator]

/-- Exact residual ablation removes the generated edge again. This is the
causal control distinguishing residual-driven generator genesis from a merely
pre-existing transition. -/
theorem stage17_exact_residual_ablation_restores_failure :
    (¬ Nonempty (FreePath (Stage17SynthesizeGenerator [] true) false true)) ∧
    Nonempty
      (FreePath
        (Stage17SynthesizeGenerator
          (finiteResidualSelect Stage13G0 Stage13Candidates []) true)
        false true) :=
  ⟨stage17_empty_residual_generator_has_no_cross,
   stage17_residual_directly_generates_cross⟩

/-- No newly selected residual sources means the generated relation is
pointwise empty. -/
theorem stage17_no_new_residual_no_generator_evidence (target x y : Bool) :
    Stage17SynthesizeGenerator [] target x y = Empty := by
  simp [Stage17SynthesizeGenerator]

/-- Stage-17 direct-generator-genesis certificate.

This removes Stage 16's supplied `{src,dst}` constructor-schema object from the
developmental path:
* cold: no residual source data, so direct synthesis yields no cross evidence;
* verified residual selection produces source data;
* that data is compiled directly to the raw Type-valued generator relation;
* the free continuation closure then reaches the previously unreachable target;
* exact residual ablation removes that reachability again.

The remaining supplied boundary is now narrower and explicit: the generic
meta-rule `selected source + protected target ↦ raw directed generator evidence`
is still fixed. Stage 17 therefore eliminates the schema *representation*, not
the final meta-level rule that interprets residual data as new raw possibility. -/
theorem reconstruction_stage17_direct_generator_genesis_certificate :
    (¬ Nonempty (FreePath (Stage17SynthesizeGenerator [] true) false true)) ∧
    Nonempty
      (FreePath
        (Stage17SynthesizeGenerator
          (finiteResidualSelect Stage13G0 Stage13Candidates []) true)
        false true) :=
  stage17_exact_residual_ablation_restores_failure

end MathGraph.Calculus
