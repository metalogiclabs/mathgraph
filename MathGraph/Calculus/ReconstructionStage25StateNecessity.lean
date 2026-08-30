import MathGraph.Calculus.ReconstructionStage24HistoryQuotient

universe u v

namespace MathGraph.Calculus

/-- If no selective observational state is retained, the strongest state that
can be regenerated from the current bedrock alone is full incoming
reachability equivalence over every endogenous source. -/
def Stage25FullReachabilityEq
    {Ω : Type u} (G : Ω → Ω → Type v) (x y : Ω) : Prop :=
  ∀ k : Ω, ProbeObservation G k x = ProbeObservation G k y

/-- Once the current state is regenerated as *all* endogenous reachability
observations, no further endogenous source can be a residual: every candidate
measurement has already been included by construction. -/
theorem stage25_fullReachabilityEq_no_endogenous_residual
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (hFull : Stage25FullReachabilityEq G x y) :
    ¬ ∃ k : Ω, ProbeObservation G k x ≠ ProbeObservation G k y := by
  rintro ⟨k, hk⟩
  exact hk (hFull k)

/-- Equivalent formulation in the Stage-22 residual vocabulary: the fully
regenerated interface cannot contain an endogenous residual source. -/
theorem stage25_fullReachabilityEq_no_probeResidual
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (hFull : Stage25FullReachabilityEq G x y) :
    ¬ ∃ k : Ω,
      Stage25FullReachabilityEq G x y ∧
      ProbeObservation G k x ≠ ProbeObservation G k y := by
  rintro ⟨k, _hAgain, hk⟩
  exact hk (hFull k)

/-- The one-way Bool bedrock exhibits the causal contrast. With the selective
empty interface, Stage 23 has an endogenous residual source. If that state is
ablated and regenerated maximally from `G`, the same developmental residual is
impossible. -/
theorem stage25_selective_state_ablation_kills_first_residual :
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
    ¬ (Stage25FullReachabilityEq oneEdgeGenerator false true ∧
       ProbeObservation oneEdgeGenerator true false ≠
         ProbeObservation oneEdgeGenerator true true) := by
  constructor
  · exact stage23_empty_history_has_endogenous_source
  · rintro ⟨hFull, hSep⟩
    exact hSep (hFull true)

/-- Stage-25 boundary certificate. Stage 24 eliminated exact source history,
but attempting to eliminate *all* current observational state by regenerating
the maximal state from the bedrock destroys endogenous residual discovery.
Therefore some non-saturated selective observational/attention state is
necessary for this residual-driven developmental mechanism. Its intensional
history is not necessary; its extensional partiality is. -/
theorem reconstruction_stage25_observational_state_necessity_certificate :
    (∀ {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω},
      Stage25FullReachabilityEq G x y →
      ¬ ∃ k : Ω, ProbeObservation G k x ≠ ProbeObservation G k y) ∧
    ProbeResidual oneEdgeGenerator
      (GeneratedInterface.probes ([] : GeneratedInterface Bool))
      true false true ∧
    ¬ (Stage25FullReachabilityEq oneEdgeGenerator false true ∧
       ProbeObservation oneEdgeGenerator true false ≠
         ProbeObservation oneEdgeGenerator true true) := by
  refine ⟨?_, stage25_selective_state_ablation_kills_first_residual⟩
  intro Ω G x y hFull
  exact stage25_fullReachabilityEq_no_endogenous_residual hFull

end MathGraph.Calculus
