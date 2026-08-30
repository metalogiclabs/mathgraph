import MathGraph.Calculus.ReconstructionStage5Refinement

universe u v w

namespace MathGraph.Calculus

/-- The observation contributed by a single source probe: whether that source
can reach the queried endpoint by a finite generated path. -/
def ProbeObservation {Ω : Type u}
    (G : Ω → Ω → Type v) (k : Ω) : Observation Ω Prop :=
  fun x => Nonempty (FreePath G k x)

/-- The golden refinement law specialized to the bedrock-generated probe
interface. Adding one probe intersects the old consequential identity with the
kernel of the new reachability observation. -/
theorem consequentialEq_extendProbe_iff
    {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (k x y : Ω) :
    ConsequentialEq (ProbedReachabilityLanguage G (extendProbe P k)) x y ↔
      ConsequentialEq (ProbedReachabilityLanguage G P) x y ∧
      ProbeObservation G k x = ProbeObservation G k y := by
  rw [probedLanguage_extendProbe_eq_extend]
  exact consequentialEq_extend_iff
    (ProbedReachabilityLanguage G P) (ProbeObservation G k) x y

/-- A probe residual is the bedrock-generated instance of the original
`ResidualWitness`: the current probes identify `x,y`, while one candidate
source probe has unequal reachability to them. -/
def ProbeResidual {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω)
    (k x y : Ω) : Prop :=
  ResidualWitness (ProbedReachabilityLanguage G P)
    (ProbeObservation G k) x y

/-- A residual probe necessarily splits a pair that all prior selected probes
failed to distinguish. This is generated information gain from bedrock paths. -/
theorem probeResidual_forces_split
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    {k x y : Ω} (r : ProbeResidual G P k x y) :
    ¬ ConsequentialEq
      (ProbedReachabilityLanguage G (extendProbe P k)) x y := by
  rw [probedLanguage_extendProbe_eq_extend]
  exact residual_forces_split r

/-- The residual also certifies strict information refinement: adding that
probe is not semantically redundant. -/
theorem probeResidual_forces_strict_refinement
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    {k x y : Ω} (r : ProbeResidual G P k x y) :
    Refines
      (ProbedReachabilityLanguage G (extendProbe P k))
      (ProbedReachabilityLanguage G P) ∧
    ¬ Refines
      (ProbedReachabilityLanguage G P)
      (ProbedReachabilityLanguage G (extendProbe P k)) := by
  rw [probedLanguage_extendProbe_eq_extend]
  exact residual_forces_strict_refinement r

/-- No residual exists exactly when the new probe is redundant relative to all
already selected probes. -/
theorem noProbeResidual_iff_redundant
    {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (k : Ω) :
    (¬ ∃ x y, ProbeResidual G P k x y) ↔
      Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k) := by
  constructor
  · intro hNo x y hEq
    classical
    by_contra hNe
    exact hNo ⟨x, y, ⟨hEq, hNe⟩⟩
  · intro hRed hExists
    rcases hExists with ⟨x, y, r⟩
    exact r.separated (hRed r.indistinguishable)

/-- Stage-6 certificate: information gain is no longer primitive. It is the
appearance of a probe residual: an old equivalence class together with a newly
selected reachability probe whose kernel cuts that class. -/
theorem reconstruction_stage6_certificate
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    {k x y : Ω} (r : ProbeResidual G P k x y) :
    Refines
      (ProbedReachabilityLanguage G (extendProbe P k))
      (ProbedReachabilityLanguage G P) ∧
    ¬ Refines
      (ProbedReachabilityLanguage G P)
      (ProbedReachabilityLanguage G (extendProbe P k)) :=
  probeResidual_forces_strict_refinement r

end MathGraph.Calculus
