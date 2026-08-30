import MathGraph.Calculus.ReconstructionStage19GenericResidualGenerator

namespace MathGraph.Calculus

/-- Stage 20 removes the final Stage-19 selection-membership gate.

A source `k` contributes raw directed generator evidence from `x` to `y`
exactly when the already reconstructed generic `ProbeResidual` holds and the
source reaches the positively oriented left endpoint. There is no selected
list, constructor tag, schema object, target parameter, or promotion compiler. -/
def Stage20Generator
    {ι Ω : Type} (G : Ω → Ω → Type) (P : ProbeFamily ι Ω) :
    Ω → Ω → Type :=
  fun x y =>
    { k : Ω //
      ProbeResidual G P k x y ∧
      ProbeObservation G k x }

/-- Orientation is still not supplied separately. A generic residual together
with positive left reachability forces failure of right reachability. -/
theorem stage20_generic_residual_derives_missing_right
    {ι Ω : Type} {G : Ω → Ω → Type} {P : ProbeFamily ι Ω}
    {x y : Ω}
    (e : Stage20Generator G P x y) :
    ¬ ProbeObservation G e.1 y := by
  rcases e with ⟨k, r, hx⟩
  intro hy
  apply r.separated
  apply propext
  constructor
  · intro _
    exact hy
  · intro _
    exact hx

/-- General negative law: when no generic residual exists for an endpoint pair,
Stage 20 has no raw generator evidence for that pair. This is the exact
residual-absence control after removing the explicit selection gate. -/
theorem stage20_no_residual_no_generator
    {ι Ω : Type} {G : Ω → Ω → Type} {P : ProbeFamily ι Ω}
    {x y : Ω}
    (hNo : ∀ k, ¬ ProbeResidual G P k x y) :
    IsEmpty (Stage20Generator G P x y) := by
  constructor
  intro e
  rcases e with ⟨k, r, _hx⟩
  exact hNo k r

/-- The original cold raw world still cannot reach the cross endpoint before
residual-derived generator evidence is admitted. -/
theorem stage20_cold_raw_closure_unreachable :
    ¬ Nonempty (FreePath Stage13G0 false true) :=
  stage13_cold_target_unreachable

/-- The existing Stage-6 generic residual alone now inhabits the raw generator
relation. No finite selector or membership certificate occurs in the term. -/
theorem stage20_generic_residual_alone_generates_cross :
    Nonempty
      (FreePath
        (Stage20Generator Stage13G0 (NoProbes Bool))
        false true) := by
  refine ⟨FreePath.ofGenerator ?_⟩
  refine ⟨false, ?_⟩
  constructor
  · exact stage19_cold_generic_residual
  · exact ⟨(.nil : FreePath Stage13G0 false false)⟩

/-- Stage-20 certificate.

The causal chain has now lost the explicit selection layer:
* the ancestor raw closure cannot cross `false → true`;
* the already reconstructed generic residual itself supplies the new raw edge;
* free continuation turns that edge into a reachable continuation;
* in the general negative case, residual absence makes the generated edge type
  empty.

This establishes that selection membership is not necessary for this finite
developmental path. It does not remove the generic residual semantics or the
free-continuation substrate. -/
theorem reconstruction_stage20_residual_closure_certificate :
    (¬ Nonempty (FreePath Stage13G0 false true)) ∧
    Nonempty
      (FreePath
        (Stage20Generator Stage13G0 (NoProbes Bool))
        false true) :=
  ⟨stage20_cold_raw_closure_unreachable,
   stage20_generic_residual_alone_generates_cross⟩

end MathGraph.Calculus
