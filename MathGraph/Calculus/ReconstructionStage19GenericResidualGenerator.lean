import MathGraph.Calculus.ReconstructionStage13Development

namespace MathGraph.Calculus

/-- Stage 19 removes the Stage-18 bespoke residual-edge record. Raw generator
    evidence is built directly from the already reconstructed generic
    `ProbeResidual`, together with selected-source membership and the positive
    orientation that the source reaches the left endpoint.

    The propositions are packaged only by Lean's generic `Subtype`; no new
    domain-specific residual structure is introduced. -/
def Stage19Generator
    {ι Ω : Type} (G : Ω → Ω → Type) (P : ProbeFamily ι Ω)
    (selected : List Ω) : Ω → Ω → Type :=
  fun x y =>
    { k : Ω //
      k ∈ selected ∧
      ProbeResidual G P k x y ∧
      ProbeObservation G k x }

/-- The right-side failure carried explicitly by the Stage-18 record is not
    needed. It follows from the generic residual inequality plus the positive
    left observation. -/
theorem stage19_generic_residual_derives_missing_right
    {ι Ω : Type} {G : Ω → Ω → Type} {P : ProbeFamily ι Ω}
    {selected : List Ω} {x y : Ω}
    (e : Stage19Generator G P selected x y) :
    ¬ ProbeObservation G e.1 y := by
  rcases e with ⟨k, hSelected, r, hx⟩
  intro hy
  apply r.separated
  apply propext
  constructor
  · intro _
    exact hy
  · intro _
    exact hx

/-- The cold Bool world already has a generic Stage-6 residual: source `false`
    reaches `false` by identity, does not reach `true`, and the empty probe
    interface identifies the endpoints. -/
theorem stage19_cold_generic_residual :
    ProbeResidual Stage13G0 (NoProbes Bool) false false true := by
  refine ⟨noProbes_consequentialEq false true, ?_⟩
  intro hEq
  have hFalse : ProbeObservation Stage13G0 false false :=
    ⟨(.nil : FreePath Stage13G0 false false)⟩
  have hTrue : ProbeObservation Stage13G0 false true := hEq.mp hFalse
  rcases hTrue with ⟨p⟩
  exact (emptyGenerator_no_false_to_true p).elim

/-- With no selected source there is no generator evidence, so free closure
    cannot manufacture the cross-endpoint continuation. -/
theorem stage19_empty_selection_has_no_cross :
    ¬ Nonempty
      (FreePath
        (Stage19Generator Stage13G0 (NoProbes Bool) [])
        false true) := by
  intro h
  rcases h with ⟨p⟩
  cases p with
  | step e rest =>
      rcases e with ⟨k, hk, _r, _hx⟩
      exact (by simpa using hk)

/-- Selecting the generic residual source is sufficient to inhabit the raw
    generator relation directly. No Stage-18 residual-edge structure is
    constructed and no target-directed compiler is invoked. -/
theorem stage19_generic_residual_directly_generates_cross :
    Nonempty
      (FreePath
        (Stage19Generator Stage13G0 (NoProbes Bool) [false])
        false true) := by
  refine ⟨FreePath.ofGenerator ?_⟩
  refine ⟨false, ?_⟩
  constructor
  · simp
  constructor
  · exact stage19_cold_generic_residual
  · exact ⟨(.nil : FreePath Stage13G0 false false)⟩

/-- Stage-19 certificate: the already existing generic residual predicate,
    rather than a newly introduced residual-edge record, inhabits the raw
    generator layer. The missing-right orientation is derived from the generic
    residual itself, and exact selected-source ablation removes reachability. -/
theorem reconstruction_stage19_generic_residual_generator_certificate :
    (¬ Nonempty
      (FreePath
        (Stage19Generator Stage13G0 (NoProbes Bool) [])
        false true)) ∧
    Nonempty
      (FreePath
        (Stage19Generator Stage13G0 (NoProbes Bool) [false])
        false true) :=
  ⟨stage19_empty_selection_has_no_cross,
   stage19_generic_residual_directly_generates_cross⟩

end MathGraph.Calculus
