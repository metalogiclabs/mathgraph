import MathGraph.Calculus.ReconstructionStage23GeneratedInterface

universe u v

namespace MathGraph.Calculus

/-- The extensional observational state induced by a generated source history.
Only the consequential identity relation is retained; source order and
multiplicity are forgotten. -/
def GeneratedObservationalState
    {Ω : Type u} (G : Ω → Ω → Type v) (I : GeneratedInterface Ω) :
    Ω → Ω → Prop :=
  fun x y => ConsequentialEq (GeneratedInterface.language G I) x y

/-- Two generated histories are observationally equivalent when they induce
exactly the same consequential identity on the carrier. -/
def GeneratedInterface.SemEq
    {Ω : Type u} (G : Ω → Ω → Type v)
    (I J : GeneratedInterface Ω) : Prop :=
  ∀ x y, GeneratedObservationalState G I x y ↔
    GeneratedObservationalState G J x y

/-- Extensional equality of observational state is exactly generated-interface
semantic equivalence. -/
theorem generatedInterface_semEq_iff_state_eq
    {Ω : Type u} {G : Ω → Ω → Type v}
    {I J : GeneratedInterface Ω} :
    GeneratedInterface.SemEq G I J ↔
      GeneratedObservationalState G I = GeneratedObservationalState G J := by
  constructor
  · intro h
    funext x y
    exact propext (h x y)
  · intro h x y
    rw [h]

/-- Duplicating an already retained source does not change consequential
identity. This gives two genuinely different histories with one extensional
observational state. -/
theorem stage24_duplicate_source_semEq :
    GeneratedInterface.SemEq oneEdgeGenerator
      ([true] : GeneratedInterface Bool)
      ([true, true] : GeneratedInterface Bool) := by
  intro x y
  constructor
  · intro h i
    have h0 := h (0 : Fin 1)
    fin_cases i <;>
      simpa [GeneratedObservationalState, GeneratedInterface.language,
        GeneratedInterface.probes, ProbedReachabilityLanguage] using h0
  · intro h i
    have h0 := h (0 : Fin 2)
    fin_cases i
    simpa [GeneratedObservationalState, GeneratedInterface.language,
      GeneratedInterface.probes, ProbedReachabilityLanguage] using h0

/-- The histories themselves are not equal: one records one source occurrence,
the other two. -/
theorem stage24_duplicate_histories_are_distinct :
    ([true] : GeneratedInterface Bool) ≠ [true, true] := by
  intro h
  have hLen := congrArg List.length h
  simp at hLen

/-- Consequently, exact generated history is not identifiable from the
observational state it induces. -/
theorem stage24_distinct_histories_same_state :
    ([true] : GeneratedInterface Bool) ≠ [true, true] ∧
    GeneratedObservationalState oneEdgeGenerator
      ([true] : GeneratedInterface Bool) =
    GeneratedObservationalState oneEdgeGenerator
      ([true, true] : GeneratedInterface Bool) := by
  exact ⟨stage24_duplicate_histories_are_distinct,
    (generatedInterface_semEq_iff_state_eq.mp stage24_duplicate_source_semEq)⟩

/-- Any residual whose current-side requirement is only consequential identity
is invariant under replacing a history by an observationally equivalent one.
Thus downstream residual detection does not need access to the exact history. -/
theorem stage24_residual_invariant_under_semEq
    {Ω : Type u} {G : Ω → Ω → Type v}
    {I J : GeneratedInterface Ω} {k x y : Ω}
    (hIJ : GeneratedInterface.SemEq G I J)
    (r : ResidualWitness (GeneratedInterface.language G I)
      (ProbeObservation G k) x y) :
    ResidualWitness (GeneratedInterface.language G J)
      (ProbeObservation G k) x y := by
  exact ⟨(hIJ x y).mp r.indistinguishable, r.separated⟩

/-- Stage-24 certificate: source-history representation is eliminable at the
observational layer. Distinct histories can induce the same extensional state,
and residual detection transports across that quotient. What must survive is
therefore the induced consequential state, not source order or multiplicity. -/
theorem reconstruction_stage24_history_quotient_certificate :
    ([true] : GeneratedInterface Bool) ≠ [true, true] ∧
    GeneratedObservationalState oneEdgeGenerator
      ([true] : GeneratedInterface Bool) =
    GeneratedObservationalState oneEdgeGenerator
      ([true, true] : GeneratedInterface Bool) ∧
    (∀ k x y,
      ResidualWitness
        (GeneratedInterface.language oneEdgeGenerator
          ([true] : GeneratedInterface Bool))
        (ProbeObservation oneEdgeGenerator k) x y →
      ResidualWitness
        (GeneratedInterface.language oneEdgeGenerator
          ([true, true] : GeneratedInterface Bool))
        (ProbeObservation oneEdgeGenerator k) x y) := by
  refine ⟨stage24_duplicate_histories_are_distinct,
    generatedInterface_semEq_iff_state_eq.mp stage24_duplicate_source_semEq, ?_⟩
  intro k x y r
  exact stage24_residual_invariant_under_semEq
    stage24_duplicate_source_semEq r

end MathGraph.Calculus
