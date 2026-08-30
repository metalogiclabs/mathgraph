import MathGraph.Calculus.ReconstructionStage7FirstDistinction

universe u v w

namespace MathGraph.Calculus

/-- A candidate probe is distinction-changing exactly when it has at least one
residual pair under the current selected interface. -/
def ProbeHasResidual {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (k : Ω) : Prop :=
  ∃ x y, ProbeResidual G P k x y

/-- Every candidate probe is classically decidable at the semantic level into
one of two exhaustive cases: it has a residual, or it is redundant. -/
theorem probe_candidate_dichotomy
    {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (k : Ω) :
    ProbeHasResidual G P k ∨
      Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k) := by
  exact Classical.em (ProbeHasResidual G P k) |>.elim
    (fun h => Or.inl h)
    (fun h => Or.inr ((noProbeResidual_iff_redundant G P k).mp h))

/-- The two controller outcomes are mutually exclusive: a redundant probe
cannot simultaneously contain a residual witness. -/
theorem probe_candidate_exclusive
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω} {k : Ω} :
    ¬ (ProbeHasResidual G P k ∧
      Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k)) := by
  intro h
  rcases h with ⟨⟨x, y, r⟩, hRed⟩
  exact r.separated (hRed r.indistinguishable)

/-- If a residual exists, selecting the candidate is a strict information
refinement. -/
theorem probe_hasResidual_forces_strict
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω} {k : Ω}
    (h : ProbeHasResidual G P k) :
    Refines
      (ProbedReachabilityLanguage G (extendProbe P k))
      (ProbedReachabilityLanguage G P) ∧
    ¬ Refines
      (ProbedReachabilityLanguage G P)
      (ProbedReachabilityLanguage G (extendProbe P k)) := by
  rcases h with ⟨x, y, r⟩
  exact probeResidual_forces_strict_refinement r

/-- If the candidate is redundant, selecting it is semantically conservative:
no consequential equivalence class changes. -/
theorem redundantProbe_extension_conservative
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω} {k : Ω}
    (h : Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k)) :
    ∀ x y,
      ConsequentialEq
        (ProbedReachabilityLanguage G (extendProbe P k)) x y ↔
      ConsequentialEq (ProbedReachabilityLanguage G P) x y := by
  intro x y
  rw [probedLanguage_extendProbe_eq_extend]
  exact (redundant_iff_extension_conservative
    (ProbedReachabilityLanguage G P) (ProbeObservation G k)).mp h x y

/-- Complete selection law reconstructed from bedrock. For every candidate
probe, exactly the information-changing question matters:

* SPLIT: a residual exists, so adding the probe is strict refinement;
* FORGET: no residual exists, so the probe is redundant and its extension is
  observationally conservative.

The exhaustiveness uses excluded middle, while each branch's consequence is
then verified by the constructive/reflection machinery below it. -/
theorem reconstruction_stage8_selection_law
    {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) (k : Ω) :
    (ProbeHasResidual G P k ∧
      Refines
        (ProbedReachabilityLanguage G (extendProbe P k))
        (ProbedReachabilityLanguage G P) ∧
      ¬ Refines
        (ProbedReachabilityLanguage G P)
        (ProbedReachabilityLanguage G (extendProbe P k))) ∨
    (Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k) ∧
      ∀ x y,
        ConsequentialEq
          (ProbedReachabilityLanguage G (extendProbe P k)) x y ↔
        ConsequentialEq (ProbedReachabilityLanguage G P) x y) := by
  rcases probe_candidate_dichotomy G P k with hSplit | hForget
  · exact Or.inl ⟨hSplit, probe_hasResidual_forces_strict hSplit⟩
  · exact Or.inr ⟨hForget, redundantProbe_extension_conservative hForget⟩

end MathGraph.Calculus
