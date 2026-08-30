import MathGraph.Calculus.ReconstructionStage10Sufficiency

namespace MathGraph.Calculus

/-- The selected `true` probe is redundant relative to an interface that already
contains it: consequential equality under the one-probe language directly
includes equality of that probe's observation. -/
theorem trueProbe_redundant_after_first_split :
    Redundant
      (ProbedReachabilityLanguage oneEdgeGenerator FirstProbeFamily)
      (ProbeObservation oneEdgeGenerator true) := by
  intro x y hEq
  exact hEq (Sum.inr ())

/-- The one-probe interface produced by the first residual is saturated over
all possible Bool source probes. -/
theorem firstProbeFamily_saturated :
    ProbeSaturated oneEdgeGenerator FirstProbeFamily := by
  intro k
  cases k with
  | false => exact falseProbe_redundant_after_first_split
  | true => exact trueProbe_redundant_after_first_split

/-- Therefore that one selected probe is sufficient for the full all-source
reachability identity. -/
theorem firstProbeFamily_sufficient :
    ∀ x y : Bool,
      ConsequentialEq
        (ProbedReachabilityLanguage oneEdgeGenerator FirstProbeFamily) x y ↔
      ConsequentialEq
        (IncomingReachabilityLanguage oneEdgeGenerator) x y :=
  fun x y => saturated_iff_full_consequentialEq firstProbeFamily_saturated x y

/-- The zero-probe interface is not sufficient: it identifies `false` and
`true`, while the full reachability language distinguishes them. -/
theorem noProbes_not_sufficient :
    ¬ (∀ x y : Bool,
      ConsequentialEq
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool)) x y ↔
      ConsequentialEq
        (IncomingReachabilityLanguage oneEdgeGenerator) x y) := by
  intro hSufficient
  have hEmpty :
      ConsequentialEq
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool))
        false true :=
    noProbes_consequentialEq false true
  have hFull :
      ConsequentialEq
        (IncomingReachabilityLanguage oneEdgeGenerator) false true :=
    (hSufficient false true).mp hEmpty
  have hGenerated : Nonempty (GeneratedIdentity oneEdgeGenerator false true) :=
    consequentialEq_to_nonempty_generatedIdentity hFull
  rcases hGenerated with ⟨gid⟩
  exact (oneWay_not_generatedIdentity gid).elim

/-- First complete minimal-sufficient-interface genesis certificate.

Starting with no observation coordinates:
1. zero probes are insufficient;
2. a raw reachability residual selects source `true`;
3. the resulting one-probe interface is saturated;
4. saturation makes it equivalent to the full all-source identity interface.

For this two-state world, one generated probe is therefore both necessary
(relative to the zero-probe predecessor) and sufficient. -/
theorem reconstruction_stage11_minimal_sufficient_certificate :
    (¬ (∀ x y : Bool,
      ConsequentialEq
        (ProbedReachabilityLanguage oneEdgeGenerator (NoProbes Bool)) x y ↔
      ConsequentialEq
        (IncomingReachabilityLanguage oneEdgeGenerator) x y)) ∧
    (∀ x y : Bool,
      ConsequentialEq
        (ProbedReachabilityLanguage oneEdgeGenerator FirstProbeFamily) x y ↔
      ConsequentialEq
        (IncomingReachabilityLanguage oneEdgeGenerator) x y) :=
  ⟨noProbes_not_sufficient, firstProbeFamily_sufficient⟩

end MathGraph.Calculus
