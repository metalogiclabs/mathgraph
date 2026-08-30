import MathGraph.Calculus.ActiveBoundaryCompression

namespace MathGraph.Calculus

/-- A verifier interaction history stores only previously ordered tasks.  Its
selective observational state is reconstructed from their targets rather than
supplied independently. -/
abbrev VerifierTaskHistory (Ω : Type) := List (Stage26TaskBoundary Ω)

/-- Each previously verified target becomes a retained reachability coordinate.
The observation semantics still comes entirely from the raw generator `G`. -/
def VerifierTaskHistory.targets {Ω : Type}
    (H : VerifierTaskHistory Ω) : GeneratedInterface Ω :=
  H.map (fun t => t.target)

/-- The current active boundary consists of past verifier interactions plus one
ordered task.  There is no independently supplied `ProbeFamily` field. -/
structure GeneratedVerifierBoundary (Ω : Type) where
  history : VerifierTaskHistory Ω
  current : Stage26TaskBoundary Ω

namespace GeneratedVerifierBoundary

/-- Selective observation is generated from prior verifier targets. -/
def probes {Ω : Type} (B : GeneratedVerifierBoundary Ω) :
    ProbeFamily (Fin B.history.targets.length) Ω :=
  GeneratedInterface.probes B.history.targets

/-- The packed active-boundary view is derived, not primitive. -/
def active {Ω : Type} (B : GeneratedVerifierBoundary Ω) : ActiveBoundary Ω :=
  { ι := Fin B.history.targets.length
    probes := B.probes
    task := B.current }

/-- Learning the current verifier request retains its target as the next
selective reachability coordinate. -/
def learn {Ω : Type} (B : GeneratedVerifierBoundary Ω) :
    GeneratedVerifierBoundary Ω :=
  { history := B.history ++ [B.current]
    current := B.current }

end GeneratedVerifierBoundary

/-- Canonical one-way verifier request used for the finite deciding witness. -/
def Stage28BoolTask : Stage26TaskBoundary Bool := ⟨false, true⟩

def Stage28ColdBoundary : GeneratedVerifierBoundary Bool :=
  { history := []
    current := Stage28BoolTask }

/-- Before any verifier interaction has been retained, the generated selective
state is empty and the current task target supplies a genuine new residual. -/
theorem stage28_current_task_target_is_new_residual :
    ProbeResidual oneEdgeGenerator Stage28ColdBoundary.probes
      Stage28ColdBoundary.current.target
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.target := by
  simpa [Stage28ColdBoundary, Stage28BoolTask,
    GeneratedVerifierBoundary.probes, VerifierTaskHistory.targets] using
    stage23_empty_history_has_endogenous_source

/-- The same current task is operationally oriented and the task target gives
the positive reachability witness needed by the Stage-20 developmental edge. -/
theorem stage28_current_task_licenses_development :
    Nonempty
      (Stage20Generator oneEdgeGenerator Stage28ColdBoundary.probes
        Stage28ColdBoundary.current.source Stage28ColdBoundary.current.target) := by
  refine ⟨⟨true, ?_⟩⟩
  constructor
  · simpa [Stage28ColdBoundary, Stage28BoolTask,
      GeneratedVerifierBoundary.probes, VerifierTaskHistory.targets] using
      stage23_empty_history_has_endogenous_source
  · exact ⟨one_generator_creates_cross_transition⟩

/-- Retaining the completed task regenerates the previously independent
selective state: the task history becomes exactly the singleton generated
interface `[true]`. -/
theorem stage28_learning_generates_selective_state :
    (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets =
      ([true] : GeneratedInterface Bool) := by
  rfl

/-- The generated post-task state strictly refines the pre-task state. -/
theorem stage28_task_history_strictly_refines_observation :
    Refines
      (GeneratedInterface.language oneEdgeGenerator
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets)
      (GeneratedInterface.language oneEdgeGenerator
        Stage28ColdBoundary.history.targets) ∧
    ¬ Refines
      (GeneratedInterface.language oneEdgeGenerator
        Stage28ColdBoundary.history.targets)
      (GeneratedInterface.language oneEdgeGenerator
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets) := by
  simpa [Stage28ColdBoundary, Stage28BoolTask,
    GeneratedVerifierBoundary.learn, VerifierTaskHistory.targets] using
    stage23_generated_history_strictly_refines

/-- Once the current verifier target has been retained as an observation
coordinate, the exact residual that caused the update is discharged. -/
theorem stage28_generated_state_discharges_residual :
    ¬ ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets)
      true false true := by
  intro r
  have hEq := r.indistinguishable (0 : Fin 1)
  exact r.separated hEq

/-- Full endogenization still fails at the symmetry boundary.  If the ordered
verifier request is erased, the cold two-point world admits no canonical
orientation that is both endpoint-presentation invariant and rename
-equivariant. -/
theorem stage28_external_order_remains_irreducible_in_symmetric_seed :
    ¬ Nonempty Stage21CanonicalOrientation :=
  stage21_no_canonical_orientation_from_symmetric_pair

/-- Stage-28 self-hosting-boundary certificate.

The selective observational face of the active boundary is no longer an
independent primitive: a stream of externally ordered verifier tasks generates
it recursively from prior task targets and bedrock reachability.  The current
task target can create the next residual, retaining that task strictly refines
the observational state, and the triggering residual is then discharged.

But complete boundary endogenization is blocked by the Stage-21 symmetry
counterexample: without externally supplied ordered evidence there is no
canonical operational orientation in the symmetric cold seed.  Relative to
this mechanism, the surviving exogenous role is therefore symmetry-breaking
verifier/task order, not a separately supplied observation family. -/
theorem verifier_boundary_endogenization_certificate :
    ProbeResidual oneEdgeGenerator Stage28ColdBoundary.probes
      Stage28ColdBoundary.current.target
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.target ∧
    Nonempty
      (Stage20Generator oneEdgeGenerator Stage28ColdBoundary.probes
        Stage28ColdBoundary.current.source Stage28ColdBoundary.current.target) ∧
    ((GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets =
      ([true] : GeneratedInterface Bool)) ∧
    (Refines
      (GeneratedInterface.language oneEdgeGenerator
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets)
      (GeneratedInterface.language oneEdgeGenerator
        Stage28ColdBoundary.history.targets) ∧
     ¬ Refines
      (GeneratedInterface.language oneEdgeGenerator
        Stage28ColdBoundary.history.targets)
      (GeneratedInterface.language oneEdgeGenerator
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets)) ∧
    (¬ ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.targets)
      true false true) ∧
    (¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage28_current_task_target_is_new_residual,
    stage28_current_task_licenses_development,
    stage28_learning_generates_selective_state,
    stage28_task_history_strictly_refines_observation,
    stage28_generated_state_discharges_residual,
    stage28_external_order_remains_irreducible_in_symmetric_seed⟩

end MathGraph.Calculus
