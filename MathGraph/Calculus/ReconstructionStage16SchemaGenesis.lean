import MathGraph.Calculus.ReconstructionStage15RecursiveDevelopment

namespace MathGraph.Calculus

/-- Stage 16 removes the finite named constructor-kind enumeration used in
Stages 14-15. A constructor schema is now ordinary endpoint data: a directed
edge to be installed. There is no `idle/cross` sum type at this layer. -/
structure Stage16Schema where
  src : Bool
  dst : Bool
  deriving DecidableEq

/-- Compiling a schema installs exactly the directed edge described by its
data. The surrounding free-path closure still supplies identity/composition. -/
def Stage16Compile (s : Stage16Schema) : Bool → Bool → Type :=
  fun x y => if x = s.src ∧ y = s.dst then Unit else Empty

/-- The initial schema language is empty: no constructor schema is licensed. -/
def Stage16K0 : List Stage16Schema := []

/-- Residual synthesis is parametric rather than a lookup in a fixed enum.
Every newly selected residual source is turned into a schema targeting the
currently protected target endpoint. -/
def Stage16Synthesize (newSources : List Bool) (target : Bool) : List Stage16Schema :=
  newSources.map (fun src => { src := src, dst := target })

/-- The developmental update extends the current schema language with exactly
the synthesized schemas. -/
def Stage16DevelopLanguage (K : List Stage16Schema)
    (newSources : List Bool) (target : Bool) : List Stage16Schema :=
  Stage16Synthesize newSources target ++ K

/-- The concrete schema required to install the missing cold transition. -/
def Stage16Needed : Stage16Schema := { src := false, dst := true }

/-- The needed schema is not latent in the cold language. -/
theorem stage16_needed_not_present_cold : Stage16Needed ∉ Stage16K0 := by
  simp [Stage16K0]

/-- Stage-13's verified residual selector provides the source data from which
the new schema is synthesized; the schema was not chosen from a finite
constructor-kind catalogue. -/
theorem stage16_residual_synthesizes_needed_schema :
    Stage16Synthesize
      (finiteResidualSelect Stage13G0 Stage13Candidates []) true =
      [Stage16Needed] := by
  rw [stage13_selection_is_endogenous]
  rfl

/-- After one developmental language update, the freshly synthesized schema is
licensed. -/
theorem stage16_needed_present_after_development :
    Stage16Needed ∈
      Stage16DevelopLanguage Stage16K0
        (finiteResidualSelect Stage13G0 Stage13Candidates []) true := by
  rw [stage13_selection_is_endogenous]
  simp [Stage16DevelopLanguage, Stage16Synthesize, Stage16K0, Stage16Needed]

/-- Compiling the synthesized schema creates the previously unavailable
cross-endpoint continuation. -/
theorem stage16_synthesized_schema_reaches_target :
    Nonempty (FreePath (Stage16Compile Stage16Needed) false true) := by
  refine ⟨FreePath.ofGenerator ?_⟩
  change Unit
  exact ()

/-- Exact schema ablation restores the original cold obstruction: without the
synthesized schema, the raw world remains `Stage13G0`. -/
theorem stage16_exact_schema_ablation_restores_failure :
    Stage16Needed ∉ Stage16K0 ∧
    ¬ Nonempty (FreePath Stage13G0 false true) :=
  ⟨stage16_needed_not_present_cold, stage13_cold_target_unreachable⟩

/-- Negative law: no newly selected residual sources means no schema genesis. -/
theorem stage16_no_new_residual_no_schema_genesis (target : Bool) :
    Stage16Synthesize [] target = [] := by
  rfl

/-- Stage-16 schema-genesis certificate.

This closes the specific Stage-15 boundary caused by the finite named
constructor-kind datatype:
* the cold language contains no constructor schema at all;
* a verified residual supplies source data;
* a fresh directed-edge schema value is synthesized parametrically from that
  residual and the protected target endpoint;
* compiling the new schema changes reachable closure;
* deleting it restores the cold obstruction;
* no new residual source yields no schema extension.

This does NOT yet eliminate every metalanguage assumption: the generic
`Stage16Schema {src,dst}` shape and protected target endpoint are still supplied.
The next boundary is genesis of the schema-forming operation/shape itself. -/
theorem reconstruction_stage16_schema_genesis_certificate :
    Stage16Needed ∉ Stage16K0 ∧
    Stage16Synthesize
      (finiteResidualSelect Stage13G0 Stage13Candidates []) true =
      [Stage16Needed] ∧
    Stage16Needed ∈
      Stage16DevelopLanguage Stage16K0
        (finiteResidualSelect Stage13G0 Stage13Candidates []) true ∧
    Nonempty (FreePath (Stage16Compile Stage16Needed) false true) ∧
    ¬ Nonempty (FreePath Stage13G0 false true) :=
  ⟨stage16_needed_not_present_cold,
   stage16_residual_synthesizes_needed_schema,
   stage16_needed_present_after_development,
   stage16_synthesized_schema_reaches_target,
   stage13_cold_target_unreachable⟩

end MathGraph.Calculus