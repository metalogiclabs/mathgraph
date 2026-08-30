import MathGraph.Calculus.ActiveBoundaryCompression

namespace MathGraph.Calculus

/-- A verifier interaction history stores only previously ordered tasks. Its
selective observational state is reconstructed from their ordered sources
rather than supplied independently. -/
abbrev VerifierTaskHistory (Ω : Type) := List (Stage26TaskBoundary Ω)

/-- Each previously verified source becomes a retained reachability coordinate.
The observation semantics still comes entirely from the raw generator `G`. -/
def VerifierTaskHistory.sources {Ω : Type}
    (H : VerifierTaskHistory Ω) : GeneratedInterface Ω :=
  H.map (fun t => t.source)

/-- The current active boundary consists of past verifier interactions plus one
ordered task. There is no independently supplied `ProbeFamily` field. -/
structure GeneratedVerifierBoundary (Ω : Type) where
  history : VerifierTaskHistory Ω
  current : Stage26TaskBoundary Ω

namespace GeneratedVerifierBoundary

/-- Selective observation is generated from prior verifier sources. -/
def probes {Ω : Type} (B : GeneratedVerifierBoundary Ω) :
    ProbeFamily (Fin B.history.sources.length) Ω :=
  GeneratedInterface.probes B.history.sources

/-- The packed active-boundary view is derived, not primitive. -/
def active {Ω : Type} (B : GeneratedVerifierBoundary Ω) : ActiveBoundary Ω :=
  { ι := Fin B.history.sources.length
    probes := B.probes
    task := B.current }

/-- Learning the current verifier request retains its source as the next
selective reachability coordinate. -/
def learn {Ω : Type} (B : GeneratedVerifierBoundary Ω) :
    GeneratedVerifierBoundary Ω :=
  { history := B.history ++ [B.current]
    current := B.current }

end GeneratedVerifierBoundary

/-- Canonical ordered verifier request used for the finite deciding witness. -/
def Stage28BoolTask : Stage26TaskBoundary Bool := ⟨false, true⟩

def Stage28ColdBoundary : GeneratedVerifierBoundary Bool :=
  { history := []
    current := Stage28BoolTask }

/-- Before any verifier interaction has been retained, the generated selective
state is empty. The current ordered task source itself supplies the cold
residual witness from the bedrock generator. -/
theorem stage28_current_task_source_is_new_residual :
    ProbeResidual Stage13G0 Stage28ColdBoundary.probes
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.target := by
  refine ⟨?_, ?_⟩
  · intro i
    exact Fin.elim0 i
  · exact stage19_cold_generic_residual.separated

/-- The same current task source has the positive reachability witness needed by
Stage 20, so the externally ordered request licenses the developmental edge
without an independently supplied observation family. -/
theorem stage28_current_task_licenses_development :
    Nonempty
      (Stage20Generator Stage13G0 Stage28ColdBoundary.probes
        Stage28ColdBoundary.current.source Stage28ColdBoundary.current.target) := by
  refine ⟨⟨false, ?_⟩⟩
  constructor
  · exact stage28_current_task_source_is_new_residual
  · exact ⟨(.nil : FreePath Stage13G0 false false)⟩

/-- Retaining the completed task regenerates the previously independent
selective state: the task history becomes exactly the singleton generated
interface `[false]`. -/
theorem stage28_learning_generates_selective_state :
    (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources =
      ([false] : GeneratedInterface Bool) := by
  rfl

/-- The generated post-task state strictly refines the pre-task state. -/
theorem stage28_task_history_strictly_refines_observation :
    Refines
      (GeneratedInterface.language Stage13G0
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)
      (GeneratedInterface.language Stage13G0
        Stage28ColdBoundary.history.sources) ∧
    ¬ Refines
      (GeneratedInterface.language Stage13G0
        Stage28ColdBoundary.history.sources)
      (GeneratedInterface.language Stage13G0
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources) := by
  constructor
  · intro x y _h i
    exact Fin.elim0 i
  · intro h
    have hOld : ConsequentialEq
        (GeneratedInterface.language Stage13G0
          Stage28ColdBoundary.history.sources) false true := by
      intro i
      exact Fin.elim0 i
    have hNew : ConsequentialEq
        (GeneratedInterface.language Stage13G0
          (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)
        false true := h hOld
    have hEq := hNew (0 : Fin 1)
    exact stage19_cold_generic_residual.separated hEq

/-- Once the current verifier source has been retained as an observation
coordinate, the exact residual that caused the update is discharged. -/
theorem stage28_generated_state_discharges_residual :
    ¬ ProbeResidual Stage13G0
      (GeneratedInterface.probes
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)
      false false true := by
  intro r
  have hEq := r.indistinguishable (0 : Fin 1)
  exact r.separated hEq

/-- Full endogenization still fails at the symmetry boundary. If the ordered
verifier request is erased, the cold two-point world admits no canonical
orientation that is both endpoint-presentation invariant and rename-
equivariant. -/
theorem stage28_external_order_remains_irreducible_in_symmetric_seed :
    ¬ Nonempty Stage21CanonicalOrientation :=
  stage21_no_canonical_orientation_from_symmetric_pair

/-- Stage-28 self-hosting-boundary certificate.

The selective observational face of the active boundary is no longer an
independent primitive: a stream of externally ordered verifier tasks generates
it recursively from prior task sources and bedrock reachability. The current
task source creates the next residual, retaining that task strictly refines the
observational state, and the triggering residual is then discharged.

But complete boundary endogenization is blocked by the Stage-21 symmetry
counterexample: without externally supplied ordered evidence there is no
canonical operational orientation in the symmetric cold seed. Relative to
this mechanism, the surviving exogenous role is therefore symmetry-breaking
verifier/task order, not a separately supplied observation family. -/
theorem verifier_boundary_endogenization_certificate :
    ProbeResidual Stage13G0 Stage28ColdBoundary.probes
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.source
      Stage28ColdBoundary.current.target ∧
    Nonempty
      (Stage20Generator Stage13G0 Stage28ColdBoundary.probes
        Stage28ColdBoundary.current.source Stage28ColdBoundary.current.target) ∧
    ((GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources =
      ([false] : GeneratedInterface Bool)) ∧
    (Refines
      (GeneratedInterface.language Stage13G0
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)
      (GeneratedInterface.language Stage13G0
        Stage28ColdBoundary.history.sources) ∧
     ¬ Refines
      (GeneratedInterface.language Stage13G0
        Stage28ColdBoundary.history.sources)
      (GeneratedInterface.language Stage13G0
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)) ∧
    (¬ ProbeResidual Stage13G0
      (GeneratedInterface.probes
        (GeneratedVerifierBoundary.learn Stage28ColdBoundary).history.sources)
      false false true) ∧
    (¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage28_current_task_source_is_new_residual,
    stage28_current_task_licenses_development,
    stage28_learning_generates_selective_state,
    stage28_task_history_strictly_refines_observation,
    stage28_generated_state_discharges_residual,
    stage28_external_order_remains_irreducible_in_symmetric_seed⟩

end MathGraph.Calculus
