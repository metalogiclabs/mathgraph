import MathGraph.Calculus.ReconstructionStage6Residual

namespace MathGraph.Calculus

/-- The initial observation interface contains no probes at all. -/
def NoProbes (Ω : Type) : ProbeFamily Empty Ω :=
  fun e => nomatch e

/-- With no selected probes, every pair of endpoints is observationally
indistinguishable: there is no coordinate at which they could disagree. -/
theorem noProbes_consequentialEq
    {Ω : Type} {G : Ω → Ω → Type} (x y : Ω) :
    ConsequentialEq (ProbedReachabilityLanguage G (NoProbes Ω)) x y := by
  intro i
  exact nomatch i

/-- In the one-way raw world `false → true`, using `true` as a source probe
separates `false` from `true`: `true` reaches itself by the zero path, but it
cannot reach `false`. -/
theorem trueProbe_separates_false_true :
    ProbeObservation oneEdgeGenerator true false ≠
      ProbeObservation oneEdgeGenerator true true := by
  intro hEq
  have hReverse : Nonempty (FreePath oneEdgeGenerator true false) :=
    Eq.mp hEq.symm ⟨(.nil : FreePath oneEdgeGenerator true true)⟩
  rcases hReverse with ⟨p⟩
  exact (oneEdge_no_reverse p).elim

/-- Therefore, relative to the completely empty observation interface, the
source `true` is already a residual probe. No pre-existing test coordinate is
needed to state the old equivalence class. -/
theorem first_probe_residual :
    ProbeResidual oneEdgeGenerator (NoProbes Bool) true false true :=
  ⟨noProbes_consequentialEq false true,
   trueProbe_separates_false_true⟩

/-- Selecting that residual probe creates the first observational distinction. -/
theorem first_probe_creates_distinction :
    ¬ ConsequentialEq
      (ProbedReachabilityLanguage oneEdgeGenerator
        (extendProbe (NoProbes Bool) true))
      false true :=
  probeResidual_forces_split first_probe_residual

/-- And because the previous interface had no probes, this first split is a
strict refinement from total observational indistinguishability. -/
theorem first_probe_is_strict_information_gain :
    Refines
      (ProbedReachabilityLanguage oneEdgeGenerator
        (extendProbe (NoProbes Bool) true))
      (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool)) ∧
    ¬ Refines
      (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool))
      (ProbedReachabilityLanguage oneEdgeGenerator
        (extendProbe (NoProbes Bool) true)) :=
  probeResidual_forces_strict_refinement first_probe_residual

/-- Stage-7 certificate: an observational distinction can be generated from a
zero-probe interface by selecting a residual source from raw directed bedrock.
The boundary positions and directed possibility already exist, but the test
coordinate is not assumed: the observation language grows from `Empty` to one
probe exactly because that probe separates a formerly undivided class. -/
theorem reconstruction_stage7_certificate :
    ConsequentialEq
      (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool))
      false true ∧
    ¬ ConsequentialEq
      (ProbedReachabilityLanguage oneEdgeGenerator
        (extendProbe (NoProbes Bool) true))
      false true :=
  ⟨noProbes_consequentialEq false true,
   first_probe_creates_distinction⟩

end MathGraph.Calculus
