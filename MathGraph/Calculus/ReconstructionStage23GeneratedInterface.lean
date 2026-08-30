import MathGraph.Calculus.ReconstructionStage22MeasurementGenesis

universe u v

namespace MathGraph.Calculus

/-- A generated interface is just its finite history of endogenous sources.
No external `ProbeFamily` is stored in the developmental state. -/
abbrev GeneratedInterface (Ω : Type u) := List Ω

/-- Interpret generated interface history back into the generic probe family
already used by the reconstruction. Each retained source receives exactly its
bedrock reachability observation. -/
def GeneratedInterface.probes
    {Ω : Type u} (I : GeneratedInterface Ω) : ProbeFamily (Fin I.length) Ω :=
  fun i => I.get i

/-- The observational language of a generated interface is therefore derived
entirely from the bedrock generator and its retained source history. -/
def GeneratedInterface.language
    {Ω : Type u} (G : Ω → Ω → Type v) (I : GeneratedInterface Ω) :
    Language (Fin I.length) Ω Prop :=
  ProbedReachabilityLanguage G (GeneratedInterface.probes I)

/-- Appending a newly discovered endogenous source extends the generated
interface without supplying a new observation function. -/
def GeneratedInterface.extend
    {Ω : Type u} (I : GeneratedInterface Ω) (k : Ω) : GeneratedInterface Ω :=
  I ++ [k]

/-- Empty generated history induces universal consequential identity: there is
no retained coordinate at which two endpoints can disagree. -/
theorem generatedInterface_empty_identifies
    {Ω : Type u} {G : Ω → Ω → Type v} (x y : Ω) :
    ConsequentialEq
      (GeneratedInterface.language G ([] : GeneratedInterface Ω)) x y := by
  intro i
  exact Fin.elim0 i

/-- In the one-way Bool bedrock, the generated history bootstraps itself:
starting from no retained measurements, the endogenous source `true` separates
`false` from `true`. -/
theorem stage23_empty_history_has_endogenous_source :
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true := by
  refine ⟨generatedInterface_empty_identifies false true, ?_⟩
  exact trueProbe_separates_false_true

/-- The first retained source history strictly refines the empty generated
interface. This is the same information gain as Stage 22, but `P` is no longer
an input state: it is reconstructed from history. -/
theorem stage23_generated_history_strictly_refines :
    Refines
      (GeneratedInterface.language oneEdgeGenerator
        ([true] : GeneratedInterface Bool))
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool)) ∧
    ¬ Refines
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool))
      (GeneratedInterface.language oneEdgeGenerator
        ([true] : GeneratedInterface Bool)) := by
  constructor
  · intro x y _h i
    exact Fin.elim0 i
  · intro h
    have hOld : ConsequentialEq
        (GeneratedInterface.language oneEdgeGenerator
          ([] : GeneratedInterface Bool))
        false true := generatedInterface_empty_identifies false true
    have hNew : ConsequentialEq
        (GeneratedInterface.language oneEdgeGenerator
          ([true] : GeneratedInterface Bool))
        false true := h hOld
    have hEq :
        ProbeObservation oneEdgeGenerator true false =
          ProbeObservation oneEdgeGenerator true true := hNew 0
    exact trueProbe_separates_false_true hEq

/-- Exact ablation: retaining no generated source leaves the endpoints
identified; the information gain disappears with the generated history. -/
theorem stage23_history_ablation_restores_collapse :
    ConsequentialEq
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool))
      false true :=
  generatedInterface_empty_identifies false true

/-- Stage-23 certificate: interface state is reconstructible from generated
source history. The developmental state need not carry an arbitrary supplied
`ProbeFamily`; it can carry only endogenous source history, whose measurement
semantics are generated from bedrock paths. -/
theorem reconstruction_stage23_generated_interface_certificate :
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
    (Refines
      (GeneratedInterface.language oneEdgeGenerator
        ([true] : GeneratedInterface Bool))
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool)) ∧
     ¬ Refines
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool))
      (GeneratedInterface.language oneEdgeGenerator
        ([true] : GeneratedInterface Bool))) ∧
    ConsequentialEq
      (GeneratedInterface.language oneEdgeGenerator
        ([] : GeneratedInterface Bool))
      false true := by
  exact ⟨stage23_empty_history_has_endogenous_source,
    stage23_generated_history_strictly_refines,
    stage23_history_ablation_restores_collapse⟩

end MathGraph.Calculus
