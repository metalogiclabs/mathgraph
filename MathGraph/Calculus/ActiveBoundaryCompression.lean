import MathGraph.Calculus.CanonicalDevelopmentalCalculus

namespace MathGraph.Calculus

/-- A single active boundary packages the two surviving boundary roles:
selective extensional observation and externally ordered task orientation.

This deliberately tests structural compression only.  The ablations below ask
whether either informational role can actually be erased after packaging. -/
structure ActiveBoundary (Ω : Type) where
  ι : Type
  probes : ProbeFamily ι Ω
  task : Stage26TaskBoundary Ω

/-- Three top-level objects: endpoints, raw generators, and one active boundary. -/
structure ActiveDevelopmentalBasis where
  Ω : Type
  G : Ω → Ω → Type
  boundary : ActiveBoundary Ω

namespace ActiveDevelopmentalBasis

/-- Continuation remains generated from raw directed possibility. -/
def Path (B : ActiveDevelopmentalBasis) (x y : B.Ω) : Type :=
  FreePath B.G x y

/-- Consequential identity reads only the selective observational face of the
active boundary. -/
def Same (B : ActiveDevelopmentalBasis) (x y : B.Ω) : Prop :=
  ConsequentialEq
    (ProbedReachabilityLanguage B.G B.boundary.probes) x y

/-- Residual detection couples the selective observational face to the ordered
task face of the same active boundary. -/
def Residual (B : ActiveDevelopmentalBasis) (k : B.Ω) : Prop :=
  ProbeResidual B.G B.boundary.probes k
    B.boundary.task.source B.boundary.task.target

/-- Operational developmental evidence uses the same packed boundary. -/
def DevelopmentalEdge (B : ActiveDevelopmentalBasis) : Type :=
  Stage20Generator B.G B.boundary.probes
    B.boundary.task.source B.boundary.task.target

end ActiveDevelopmentalBasis

/-- Every canonical four-field basis has a definitionally equivalent
three-top-level-field presentation. -/
def canonicalToActive
    (B : CanonicalDevelopmentalBasis) : ActiveDevelopmentalBasis :=
  { Ω := B.Ω
    G := B.G
    boundary :=
      { ι := B.ι
        probes := B.P
        task := B.task } }

/-- The active presentation can be unpacked back into the canonical one. -/
def activeToCanonical
    (B : ActiveDevelopmentalBasis) : CanonicalDevelopmentalBasis :=
  { Ω := B.Ω
    G := B.G
    ι := B.boundary.ι
    P := B.boundary.probes
    task := B.boundary.task }

/-- The compression preserves all four derived semantic interfaces by
construction; no behavioral content is changed by packing. -/
theorem active_boundary_compression_preserves_semantics
    (B : CanonicalDevelopmentalBasis) (x y k : B.Ω) :
    ActiveDevelopmentalBasis.Path (canonicalToActive B) x y =
      CanonicalDevelopmentalBasis.Path B x y ∧
    ActiveDevelopmentalBasis.Same (canonicalToActive B) x y =
      CanonicalDevelopmentalBasis.Same B x y ∧
    ActiveDevelopmentalBasis.Residual (canonicalToActive B) k =
      CanonicalDevelopmentalBasis.Residual B k ∧
    ActiveDevelopmentalBasis.DevelopmentalEdge (canonicalToActive B) =
      CanonicalDevelopmentalBasis.DevelopmentalEdge B := by
  exact ⟨rfl, rfl, rfl, rfl⟩

/-- The canonical cold witness in the packed three-object presentation. -/
def ActiveColdBasis : ActiveDevelopmentalBasis :=
  canonicalToActive CanonicalColdBasis

/-- Structural compression loses no verified developmental capability. -/
theorem active_boundary_three_object_sufficiency :
    Nonempty (ActiveDevelopmentalBasis.Path ActiveColdBasis false false) ∧
    ActiveDevelopmentalBasis.Same ActiveColdBasis false true ∧
    ActiveDevelopmentalBasis.Residual ActiveColdBasis false ∧
    Nonempty (ActiveDevelopmentalBasis.DevelopmentalEdge ActiveColdBasis) ∧
    (¬ Nonempty (FreePath Stage13G0 false true)) ∧
    Nonempty
      (FreePath
        (Stage13Promote (finiteResidualSelect Stage13G0 Stage13Candidates []))
        false true) := by
  exact canonical_developmental_sufficiency

/-- Internal ablation 1: packaging does not make selective observational
partiality dispensable.  Saturating that face still kills endogenous residual
development exactly as before. -/
theorem active_boundary_selectivity_is_independently_necessary :
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
    ¬ (Stage25FullReachabilityEq oneEdgeGenerator false true ∧
       ProbeObservation oneEdgeGenerator true false ≠
         ProbeObservation oneEdgeGenerator true true) :=
  stage27_selective_state_is_necessary

/-- Internal ablation 2: packaging does not make ordered orientation
dispensable.  Erasing that face restores bidirectionality and the canonical
orientation obstruction. -/
theorem active_boundary_order_is_independently_necessary :
    Nonempty (Stage26TaskGenerator Stage13G0 (NoProbes Bool)
      ⟨false, true⟩) ∧
    ((Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
      Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
     ¬ Nonempty Stage21CanonicalOrientation) :=
  stage27_internal_orientation_not_primitive

/-- Active-boundary compression certificate.

Result: the four-field canonical surface can be represented with three
*top-level objects* by packaging selective state and ordered task into one
active boundary.  But the paired internal ablations show that both faces remain
independently necessary for the verified residual-driven mechanism.  Hence this
is a structural/API compression, not an information-theoretic reduction from
four surviving roles to three. -/
theorem active_boundary_compression_certificate :
    (Nonempty (ActiveDevelopmentalBasis.Path ActiveColdBasis false false) ∧
     ActiveDevelopmentalBasis.Same ActiveColdBasis false true ∧
     ActiveDevelopmentalBasis.Residual ActiveColdBasis false ∧
     Nonempty (ActiveDevelopmentalBasis.DevelopmentalEdge ActiveColdBasis) ∧
     (¬ Nonempty (FreePath Stage13G0 false true)) ∧
     Nonempty
       (FreePath
         (Stage13Promote (finiteResidualSelect Stage13G0 Stage13Candidates []))
         false true)) ∧
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
      ¬ Nonempty Stage21CanonicalOrientation)) := by
  exact ⟨active_boundary_three_object_sufficiency,
    active_boundary_selectivity_is_independently_necessary,
    active_boundary_order_is_independently_necessary⟩

end MathGraph.Calculus
