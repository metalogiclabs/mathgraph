import MathGraph.Calculus.ReconstructionStage15RecursiveDevelopment
import MathGraph.Calculus.ReconstructionStage26TaskOrientation

namespace MathGraph.Calculus

/-- Candidate surviving basis after the destructive reconstruction.

The internal calculus keeps only:
* an endpoint carrier `Ω`;
* raw directed Type-valued generators `G`;
* a selective extensional observational interface `P`;
* an ordered external task/verifier boundary.

History and an internal orientation primitive are deliberately absent.  This
capstone uses the small universe in which the Stage-20/26 developmental edge
interface is currently formalized. -/
structure Stage27MinimalBasis where
  Ω : Type
  G : Ω → Ω → Type
  ι : Type
  P : ProbeFamily ι Ω
  task : Stage26TaskBoundary Ω

namespace Stage27MinimalBasis

/-- Free continuation is reconstructed from raw generators. -/
def Path (B : Stage27MinimalBasis) (x y : B.Ω) : Type :=
  FreePath B.G x y

/-- Measurement semantics are reconstructed from bedrock reachability. -/
def Observation (B : Stage27MinimalBasis) (k x : B.Ω) : Prop :=
  ProbeObservation B.G k x

/-- Consequential identity is reconstructed from the retained selective state. -/
def Same (B : Stage27MinimalBasis) (x y : B.Ω) : Prop :=
  ConsequentialEq (ProbedReachabilityLanguage B.G B.P) x y

/-- A new endogenous source is a residual exactly when the retained selective
state still identifies the ordered task endpoints but the generated
reachability observation separates them. -/
def Residual (B : Stage27MinimalBasis) (k : B.Ω) : Prop :=
  ProbeResidual B.G B.P k B.task.source B.task.target

/-- Raw developmental generator evidence is reconstructed from the same
residual mechanism and the external ordered task boundary. -/
def DevelopmentalEdge (B : Stage27MinimalBasis) : Type :=
  Stage20Generator B.G B.P B.task.source B.task.target

end Stage27MinimalBasis

/-- The cold Bool instance uses no hidden internal orientation primitive. -/
def Stage27ColdBasis : Stage27MinimalBasis :=
  { Ω := Bool
    G := Stage13G0
    ι := Empty
    P := NoProbes Bool
    task := ⟨false, true⟩ }

/-- The candidate basis reconstructs the full lower chain needed for a genuine
developmental event: generated continuation, generated measurement,
consequential collapse under a selective state, an endogenous residual,
raw developmental edge evidence, and a closure-changing promoted successor. -/
theorem stage27_lower_sufficiency :
    Nonempty (Stage27MinimalBasis.Path Stage27ColdBasis false false) ∧
    Stage27MinimalBasis.Same Stage27ColdBasis false true ∧
    Stage27MinimalBasis.Residual Stage27ColdBasis false ∧
    Nonempty (Stage27MinimalBasis.DevelopmentalEdge Stage27ColdBasis) ∧
    (¬ Nonempty (FreePath Stage13G0 false true)) ∧
    Nonempty
      (FreePath
        (Stage13Promote (finiteResidualSelect Stage13G0 Stage13Candidates []))
        false true) := by
  refine ⟨?_, ?_, ?_, ?_, stage13_cold_target_unreachable,
    stage13_warm_target_reachable⟩
  · exact ⟨(.nil : FreePath Stage13G0 false false)⟩
  · exact noProbes_consequentialEq false true
  · exact stage19_cold_generic_residual
  · exact stage26_forward_task_is_licensed

/-- The already verified recursive layer witnesses that the same developmental
mechanism can be reapplied to its own successor and reaches a fixed point,
while the first delta remains causally necessary for the new reachability. -/
theorem stage27_recursive_power :
    Stage15Step Stage15S0 = Stage15S1 ∧
    Stage15Step Stage15S1 = Stage15S2 ∧
    Stage15Step Stage15S2 = Stage15S2 ∧
    (¬ Nonempty (FreePath (Stage15Generator Stage15S0.world) false true)) ∧
    Nonempty (FreePath (Stage15Generator Stage15S1.world) false true) :=
  reconstruction_stage15_recursive_development_certificate

/-- Exact-history storage is not part of the surviving basis: two genuinely
different histories can induce the same extensional consequential state. -/
theorem stage27_history_not_primitive :
    GeneratedInterface.SemEq twoWayGenerator
      ([false] : GeneratedInterface Bool)
      ([true] : GeneratedInterface Bool) :=
  stage24_distinct_source_histories_semEq

/-- Selective observational partiality *is* causally necessary for this
residual-driven mechanism: replacing it by the maximal bedrock-regenerated
state removes every endogenous residual by construction. -/
theorem stage27_selective_state_is_necessary :
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
    ¬ (Stage25FullReachabilityEq oneEdgeGenerator false true ∧
       ProbeObservation oneEdgeGenerator true false ≠
         ProbeObservation oneEdgeGenerator true true) :=
  stage25_selective_state_ablation_kills_first_residual

/-- Internal orientation is not primitive: an ordered task supplies operational
direction, and ablating that external orientation restores the exact Stage-21
bidirectional/canonical-choice obstruction. -/
theorem stage27_internal_orientation_not_primitive :
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨false, true⟩) ∧
    ((Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
      Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
     ¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage26_forward_task_is_licensed,
    stage26_orientation_ablation_restores_stage21_boundary⟩

/-- Endpoint carriers and raw generators survive the destructive descent:
without endpoints there is no continuation witness at all, and without raw
generators free closure cannot create a cross-endpoint transition. -/
theorem stage27_bedrock_components_are_necessary :
    (¬ Nonempty (SomeContinuation emptyObjectGenerator)) ∧
    (¬ Nonempty (FreePath (emptyGenerator (Ω := Bool)) false true)) ∧
    Nonempty (FreePath oneEdgeGenerator false true) := by
  refine ⟨?_, ?_, ?_⟩
  · intro h
    rcases h with ⟨c⟩
    exact Empty.elim (no_objects_no_continuation c)
  · exact stage13_cold_target_unreachable
  · exact ⟨one_generator_creates_cross_transition⟩

/-- Stage-27 minimal-basis capstone.

Relative to the verified developmental capability envelope reconstructed in
Stages 1--26, the surviving basis is sufficient for continuation, generated
measurement, consequential identity, residual detection, task-directed raw
generator genesis, closure change, and finite recursive self-application.

The destructive side simultaneously certifies:
* exact history is eliminable;
* an internal orientation primitive is eliminable when orientation is supplied
  by the external ordered task/verifier boundary;
* selective observational partiality is necessary for endogenous residual
  discovery;
* endpoint typing and raw generators are necessary for continuation/change.

This is a relative minimal-sufficient-basis certificate, not a claim that the
external verifier itself has been generated internally. -/
theorem reconstruction_stage27_minimal_basis_capstone :
    (Nonempty (Stage27MinimalBasis.Path Stage27ColdBasis false false) ∧
     Stage27MinimalBasis.Same Stage27ColdBasis false true ∧
     Stage27MinimalBasis.Residual Stage27ColdBasis false ∧
     Nonempty (Stage27MinimalBasis.DevelopmentalEdge Stage27ColdBasis) ∧
     (¬ Nonempty (FreePath Stage13G0 false true)) ∧
     Nonempty
       (FreePath
         (Stage13Promote (finiteResidualSelect Stage13G0 Stage13Candidates []))
         false true)) ∧
    (Stage15Step Stage15S0 = Stage15S1 ∧
     Stage15Step Stage15S1 = Stage15S2 ∧
     Stage15Step Stage15S2 = Stage15S2 ∧
     (¬ Nonempty (FreePath (Stage15Generator Stage15S0.world) false true)) ∧
     Nonempty (FreePath (Stage15Generator Stage15S1.world) false true)) ∧
    GeneratedInterface.SemEq twoWayGenerator
      ([false] : GeneratedInterface Bool)
      ([true] : GeneratedInterface Bool) ∧
    (ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
     ¬ (Stage25FullReachabilityEq oneEdgeGenerator false true ∧
        ProbeObservation oneEdgeGenerator true false ≠
          ProbeObservation oneEdgeGenerator true true)) ∧
    (Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨false, true⟩) ∧
     ((Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
       Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
      ¬ Nonempty Stage21CanonicalOrientation)) ∧
    ((¬ Nonempty (SomeContinuation emptyObjectGenerator)) ∧
     (¬ Nonempty (FreePath (emptyGenerator (Ω := Bool)) false true)) ∧
     Nonempty (FreePath oneEdgeGenerator false true)) := by
  exact ⟨stage27_lower_sufficiency,
    stage27_recursive_power,
    stage27_history_not_primitive,
    stage27_selective_state_is_necessary,
    stage27_internal_orientation_not_primitive,
    stage27_bedrock_components_are_necessary⟩

end MathGraph.Calculus
