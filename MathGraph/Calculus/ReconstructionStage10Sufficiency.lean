import MathGraph.Calculus.ReconstructionStage9Saturation

universe u v w

namespace MathGraph.Calculus

/-- A selected probe interface is saturated when every possible source probe is
redundant relative to the consequences already selected. -/
def ProbeSaturated {ι : Type w} {Ω : Type u}
    (G : Ω → Ω → Type v) (P : ProbeFamily ι Ω) : Prop :=
  ∀ k : Ω,
    Redundant (ProbedReachabilityLanguage G P) (ProbeObservation G k)

/-- Saturation is sufficient for completeness against the full incoming
reachability language. If every omitted source probe is redundant, then the
selected interface induces exactly the same consequential identity as using
all endpoints as probes. -/
theorem saturated_iff_full_consequentialEq
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    (hSat : ProbeSaturated G P) (x y : Ω) :
    ConsequentialEq (ProbedReachabilityLanguage G P) x y ↔
      ConsequentialEq (IncomingReachabilityLanguage G) x y := by
  constructor
  · intro hSelected k
    exact hSat k hSelected
  · intro hFull i
    exact hFull (P i)

/-- At saturation, the selected interface is therefore sufficient to recover
existence of the full Type-valued generated identity. -/
theorem saturated_selectedEq_to_generatedIdentity
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    (hSat : ProbeSaturated G P) {x y : Ω}
    (h : ConsequentialEq (ProbedReachabilityLanguage G P) x y) :
    Nonempty (GeneratedIdentity G x y) :=
  consequentialEq_to_nonempty_generatedIdentity
    ((saturated_iff_full_consequentialEq hSat x y).mp h)

/-- Conversely, generated identity is always visible through any selected
probe family, saturated or not, because every selected source is one of the
full incoming reachability probes. -/
theorem generatedIdentity_to_selectedEq
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    {x y : Ω} (h : GeneratedIdentity G x y) :
    ConsequentialEq (ProbedReachabilityLanguage G P) x y := by
  have hFull : ConsequentialEq (IncomingReachabilityLanguage G) x y :=
    generatedIdentity_to_consequentialEq h
  intro i
  exact hFull (P i)

/-- Exact sufficiency certificate: once residual selection reaches saturation,
selected observational equivalence is equivalent to mere existence of the
bedrock-generated mutual continuation identity. No omitted source probe can
change the quotient. -/
theorem saturated_selectedEq_iff_nonempty_generatedIdentity
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    (hSat : ProbeSaturated G P) (x y : Ω) :
    ConsequentialEq (ProbedReachabilityLanguage G P) x y ↔
      Nonempty (GeneratedIdentity G x y) := by
  constructor
  · exact saturated_selectedEq_to_generatedIdentity hSat
  · intro h
    rcases h with ⟨gid⟩
    exact generatedIdentity_to_selectedEq gid

/-- Stage-10 certificate: residual saturation is a verifier-checkable
sufficiency condition. A saturated selected interface agrees exactly with the
full all-source observation language on consequential identity. -/
theorem reconstruction_stage10_sufficiency_certificate
    {ι : Type w} {Ω : Type u}
    {G : Ω → Ω → Type v} {P : ProbeFamily ι Ω}
    (hSat : ProbeSaturated G P) (x y : Ω) :
    ConsequentialEq (ProbedReachabilityLanguage G P) x y ↔
      ConsequentialEq (IncomingReachabilityLanguage G) x y :=
  saturated_iff_full_consequentialEq hSat x y

end MathGraph.Calculus
