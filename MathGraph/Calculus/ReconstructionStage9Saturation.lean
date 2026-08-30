import MathGraph.Calculus.ReconstructionStage8Selection

namespace MathGraph.Calculus

/-- After Stage 7, the first selected probe is source `true`. -/
def FirstProbeFamily : ProbeFamily (Sum Empty Unit) Bool :=
  extendProbe (NoProbes Bool) true

/-- The other possible Bool source probe, `false`, has the same reachability
outcome on both endpoints: `false` reaches itself by the zero path and reaches
`true` by the primitive one-way edge. -/
theorem falseProbe_observation_same :
    ∀ x y : Bool,
      ProbeObservation oneEdgeGenerator false x =
        ProbeObservation oneEdgeGenerator false y := by
  intro x y
  cases x <;> cases y
  · rfl
  · apply propext
    constructor
    · intro _
      exact ⟨FreePath.ofGenerator ()⟩
    · intro _
      exact ⟨(.nil : FreePath oneEdgeGenerator false false)⟩
  · apply propext
    constructor
    · intro _
      exact ⟨(.nil : FreePath oneEdgeGenerator false false)⟩
    · intro _
      exact ⟨FreePath.ofGenerator ()⟩
  · rfl

/-- Consequently the remaining candidate probe is redundant after the first
split: it cannot cut any equivalence class further. -/
theorem falseProbe_redundant_after_first_split :
    Redundant
      (ProbedReachabilityLanguage oneEdgeGenerator FirstProbeFamily)
      (ProbeObservation oneEdgeGenerator false) := by
  intro x y _
  exact falseProbe_observation_same x y

/-- There is therefore no residual pair for the remaining Bool source probe. -/
theorem falseProbe_has_no_residual_after_first_split :
    ¬ ProbeHasResidual oneEdgeGenerator FirstProbeFamily false := by
  intro h
  rcases h with ⟨x, y, r⟩
  exact r.separated
    (falseProbe_redundant_after_first_split r.indistinguishable)

/-- The reconstructed controller now performs a complete nontrivial cycle on
the two-state one-way world:

1. from zero probes, `true` is a residual and is selected (SPLIT);
2. after that split, the only other source probe is redundant (FORGET).

Thus the process reaches observational saturation after the first informative
selection rather than requiring a pre-supplied complete test language. -/
theorem reconstruction_stage9_saturation_certificate :
    ProbeHasResidual oneEdgeGenerator (NoProbes Bool) true ∧
    Redundant
      (ProbedReachabilityLanguage oneEdgeGenerator FirstProbeFamily)
      (ProbeObservation oneEdgeGenerator false) :=
  ⟨⟨false, true, first_probe_residual⟩,
   falseProbe_redundant_after_first_split⟩

end MathGraph.Calculus
