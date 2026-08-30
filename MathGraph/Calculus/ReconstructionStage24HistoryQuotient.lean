import MathGraph.Calculus.ReconstructionStage23GeneratedInterface

universe u v

namespace MathGraph.Calculus

/-- The extensional observational state induced by a generated source history.
Only the consequential identity relation is retained; exact source history is
forgotten. -/
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

/-- In the two-way Bool world, the two distinct sources induce the same
reachability measurement on every endpoint. Source identity is therefore more
intensional than the observational content it contributes. -/
theorem stage24_twoWay_generated_measurements_equal :
    ProbeObservation twoWayGenerator false =
      ProbeObservation twoWayGenerator true := by
  funext x
  apply propext
  constructor
  · intro _h
    cases x with
    | false => exact ⟨FreePath.ofGenerator ()⟩
    | true => exact ⟨(.nil : FreePath twoWayGenerator true true)⟩
  · intro _h
    cases x with
    | false => exact ⟨(.nil : FreePath twoWayGenerator false false)⟩
    | true => exact ⟨FreePath.ofGenerator ()⟩

/-- One-source histories containing `false` and `true` are extensionally the
same interface in the two-way world, even though the histories differ. -/
theorem stage24_distinct_source_histories_semEq :
    GeneratedInterface.SemEq twoWayGenerator
      ([false] : GeneratedInterface Bool)
      ([true] : GeneratedInterface Bool) := by
  have hLang :
      GeneratedInterface.language twoWayGenerator
        ([false] : GeneratedInterface Bool) =
      GeneratedInterface.language twoWayGenerator
        ([true] : GeneratedInterface Bool) := by
    funext i x
    have hi : i = (0 : Fin 1) := Fin.eq_zero i
    subst hi
    have hObs := congrFun stage24_twoWay_generated_measurements_equal x
    simpa [GeneratedInterface.language, GeneratedInterface.probes,
      ProbedReachabilityLanguage, ProbeObservation] using hObs
  intro x y
  rw [hLang]

/-- The histories themselves are genuinely different. -/
theorem stage24_distinct_source_histories_are_distinct :
    ([false] : GeneratedInterface Bool) ≠ [true] := by
  simp

/-- Exact history is therefore not identifiable from extensional observational
state. -/
theorem stage24_distinct_histories_same_state :
    ([false] : GeneratedInterface Bool) ≠ [true] ∧
    GeneratedObservationalState twoWayGenerator
      ([false] : GeneratedInterface Bool) =
    GeneratedObservationalState twoWayGenerator
      ([true] : GeneratedInterface Bool) := by
  exact ⟨stage24_distinct_source_histories_are_distinct,
    generatedInterface_semEq_iff_state_eq.mp
      stage24_distinct_source_histories_semEq⟩

/-- Residual detection depends only on current consequential identity, so it
transports across observationally equivalent histories. Downstream development
therefore does not need access to the exact retained source history. -/
theorem stage24_residual_invariant_under_semEq
    {Ω : Type u} {G : Ω → Ω → Type v}
    {I J : GeneratedInterface Ω} {k x y : Ω}
    (hIJ : GeneratedInterface.SemEq G I J)
    (r : ResidualWitness (GeneratedInterface.language G I)
      (ProbeObservation G k) x y) :
    ResidualWitness (GeneratedInterface.language G J)
      (ProbeObservation G k) x y := by
  exact ⟨(hIJ x y).mp r.indistinguishable, r.separated⟩

/-- Stage-24 certificate: exact source-history representation is eliminable at
this observational/residual layer. Distinct histories can induce exactly the
same extensional state, and residual detection is invariant under that
quotient. What must survive is the induced consequential state, not history. -/
theorem reconstruction_stage24_history_quotient_certificate :
    ([false] : GeneratedInterface Bool) ≠ [true] ∧
    GeneratedObservationalState twoWayGenerator
      ([false] : GeneratedInterface Bool) =
    GeneratedObservationalState twoWayGenerator
      ([true] : GeneratedInterface Bool) ∧
    (∀ k x y,
      ResidualWitness
        (GeneratedInterface.language twoWayGenerator
          ([false] : GeneratedInterface Bool))
        (ProbeObservation twoWayGenerator k) x y →
      ResidualWitness
        (GeneratedInterface.language twoWayGenerator
          ([true] : GeneratedInterface Bool))
        (ProbeObservation twoWayGenerator k) x y) := by
  refine ⟨stage24_distinct_source_histories_are_distinct,
    generatedInterface_semEq_iff_state_eq.mp
      stage24_distinct_source_histories_semEq, ?_⟩
  intro k x y r
  exact stage24_residual_invariant_under_semEq
    stage24_distinct_source_histories_semEq r

end MathGraph.Calculus
