import MathGraph.Calculus.ReconstructionStage21DirectionBoundary

universe u v w

namespace MathGraph.Calculus

/-- A measurement is not supplied as an arbitrary observation function.
Every endpoint/source already induces one canonically from the bedrock world:
ask whether that source reaches the queried endpoint by a free finite path. -/
def GeneratedMeasurement {Ω : Type u}
    (G : Ω → Ω → Type v) (k : Ω) : Observation Ω Prop :=
  ProbeObservation G k

/-- Stage 22 removes an external candidate-probe pool. A residual measurement
exists when *some endpoint of the existing carrier* induces a generated
reachability observation that separates a pair still identified by the current
interface. The candidate source is quantified over `Ω`; no list or supplied
measurement vocabulary occurs here. -/
def EndogenousProbeResidual
    {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (x y : Ω) : Prop :=
  ∃ k : Ω, ProbeResidual G P k x y

/-- Any endogenous residual constructively yields a fresh generated measurement
whose addition is a strict information refinement. No choice principle is
needed because the residual already carries its source witness. -/
theorem endogenousProbeResidual_generates_strict_measurement
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    {x y : Ω}
    (h : EndogenousProbeResidual G P x y) :
    ∃ k : Ω,
      Refines
        (ProbedReachabilityLanguage G (extendProbe P k))
        (ProbedReachabilityLanguage G P) ∧
      ¬ Refines
        (ProbedReachabilityLanguage G P)
        (ProbedReachabilityLanguage G (extendProbe P k)) := by
  rcases h with ⟨k, r⟩
  exact ⟨k, probeResidual_forces_strict_refinement r⟩

/-- Exact negative control: no endpoint can be an endogenous residual against
itself. The generated observation cannot be unequal to itself. -/
theorem no_endogenousProbeResidual_on_diagonal
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    (x : Ω) :
    ¬ EndogenousProbeResidual G P x x := by
  intro h
  rcases h with ⟨k, r⟩
  exact r.separated rfl

/-- Starting from the empty observation interface, the one-way bedrock world
already contains its first measurement source internally: `true` itself.
Nothing outside `Ω` supplies a candidate probe or its semantics. -/
theorem stage22_first_measurement_is_endogenous :
    EndogenousProbeResidual
      oneEdgeGenerator (NoProbes Bool) false true := by
  exact ⟨true, first_probe_residual⟩

/-- The endogenous residual therefore creates a strict observational refinement
from a zero-probe interface. -/
theorem stage22_first_endogenous_measurement_strictly_refines :
    ∃ k : Bool,
      Refines
        (ProbedReachabilityLanguage oneEdgeGenerator
          (extendProbe (NoProbes Bool) k))
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool)) ∧
      ¬ Refines
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool))
        (ProbedReachabilityLanguage oneEdgeGenerator
          (extendProbe (NoProbes Bool) k)) :=
  endogenousProbeResidual_generates_strict_measurement
    stage22_first_measurement_is_endogenous

/-- Stage-22 certificate.

The measurement semantics are generated from bedrock paths, and the residual
source is quantified directly over the existing endpoint carrier rather than
chosen from a supplied candidate list. From an empty observation interface an
endogenous source generates the first strict information refinement, while the
diagonal negative proves that residual genesis is not vacuous.

This removes a supplied candidate-probe pool and arbitrary measurement
function from the finite existence theorem. It does *not* erase the current
interface state `P`, the Stage-21 symmetry-breaking requirement for unique
direction, or the external verification boundary. -/
theorem reconstruction_stage22_measurement_genesis_certificate :
    EndogenousProbeResidual
      oneEdgeGenerator (NoProbes Bool) false true ∧
    (¬ EndogenousProbeResidual
      oneEdgeGenerator (NoProbes Bool) false false) ∧
    (∃ k : Bool,
      Refines
        (ProbedReachabilityLanguage oneEdgeGenerator
          (extendProbe (NoProbes Bool) k))
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool)) ∧
      ¬ Refines
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool))
        (ProbedReachabilityLanguage oneEdgeGenerator
          (extendProbe (NoProbes Bool) k))) := by
  exact ⟨stage22_first_measurement_is_endogenous,
    no_endogenousProbeResidual_on_diagonal false,
    stage22_first_endogenous_measurement_strictly_refines⟩

end MathGraph.Calculus
