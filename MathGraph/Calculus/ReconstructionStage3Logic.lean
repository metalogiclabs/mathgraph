import MathGraph.Calculus.ReconstructionStage2Profiles

universe u v

namespace MathGraph.Calculus

/-- Logical reflection of the bedrock path profile: forget the concrete path
witness and remember only whether some continuation exists. -/
def IncomingReachabilityLanguage {Ω : Type u}
    (G : Ω → Ω → Type v) : Language Ω Ω Prop :=
  fun k x => Nonempty (FreePath G k x)

/-- A concrete path transports mere incoming reachability by postcomposition. -/
def path_preserves_incomingReachability
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (p : FreePath G x y) (k : Ω) :
    Nonempty (FreePath G k x) → Nonempty (FreePath G k y) :=
  fun h => h.elim fun q => ⟨FreePath.append q p⟩

/-- Mutual finite continuation makes every incoming reachability proposition
logically equivalent. Propositional extensionality converts those two maps into
the equality required by the original consequence-language interface. -/
theorem generatedIdentity_to_consequentialEq
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : GeneratedIdentity G x y) :
    ConsequentialEq (IncomingReachabilityLanguage G) x y := by
  intro k
  apply propext
  constructor
  · exact path_preserves_incomingReachability h.1 k
  · exact path_preserves_incomingReachability h.2 k

/-- Consequential equality of the reflected reachability language can recover
existence of a forward path, but only under propositional truncation. -/
def consequentialEq_forward_nonempty
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : ConsequentialEq (IncomingReachabilityLanguage G) x y) :
    Nonempty (FreePath G x y) :=
  Eq.mp (h x) ⟨(.nil : FreePath G x x)⟩

/-- Likewise for the reverse path. -/
def consequentialEq_reverse_nonempty
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : ConsequentialEq (IncomingReachabilityLanguage G) x y) :
    Nonempty (FreePath G y x) :=
  Eq.mp (h y).symm ⟨(.nil : FreePath G y y)⟩

/-- Staying entirely in `Prop`, reflected consequential equality is sufficient
to recover the existence of generated identity data. -/
theorem consequentialEq_to_nonempty_generatedIdentity
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : ConsequentialEq (IncomingReachabilityLanguage G) x y) :
    Nonempty (GeneratedIdentity G x y) := by
  rcases consequentialEq_forward_nonempty h with ⟨p⟩
  rcases consequentialEq_reverse_nonempty h with ⟨q⟩
  exact ⟨⟨p, q⟩⟩

/-- Recovering concrete Type-valued identity data from the Prop reflection
requires an explicit choice step. This marks the logical reflection boundary
rather than hiding it inside the reconstruction. -/
noncomputable def consequentialEq_to_generatedIdentity_classical
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : ConsequentialEq (IncomingReachabilityLanguage G) x y) :
    GeneratedIdentity G x y :=
  Classical.choice (consequentialEq_to_nonempty_generatedIdentity h)

/-- Stage-3 reconstruction certificate: bedrock paths reconstruct the original
Prop-valued consequence interface. Forward reflection is constructive apart
from propositional extensionality; the reverse interface recovers only
`Nonempty` identity constructively, with concrete witness extraction isolated
behind classical choice. -/
theorem reconstruction_stage3_certificate
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    GeneratedIdentity G x y →
      ConsequentialEq (IncomingReachabilityLanguage G) x y :=
  generatedIdentity_to_consequentialEq

end MathGraph.Calculus
