/-!
# MathGraph Foundation: compositional observation and warrant preservation

Lean core theorem, with explicit trusted hypotheses. It does not certify
the hypotheses, external source bindings, or arbitrary producer statements.
-/
universe u v w

namespace MathGraphFoundation

def Warrant {S : Type u} (live : Prop) (observe : S → Prop) (s : S) : Prop :=
  live ∧ observe s

theorem compose_observation_preservation
    {S : Type u} {T : Type v} {U : Type w}
    (observeS : S → Prop) (observeT : T → Prop) (observeU : U → Prop)
    (f : S → T) (g : T → U)
    (hf : ∀ s, observeS s ↔ observeT (f s))
    (hg : ∀ t, observeT t ↔ observeU (g t))
    (s : S) :
    observeS s ↔ observeU (g (f s)) :=
  Iff.trans (hf s) (hg (f s))

theorem compose_warrant_preservation
    {S : Type u} {T : Type v} {U : Type w}
    (live : Prop)
    (observeS : S → Prop) (observeT : T → Prop) (observeU : U → Prop)
    (f : S → T) (g : T → U)
    (hf : ∀ s, observeS s ↔ observeT (f s))
    (hg : ∀ t, observeT t ↔ observeU (g t))
    (s : S) :
    Warrant live observeS s ↔ Warrant live observeU (g (f s)) := by
  constructor
  · intro h
    exact ⟨h.1, ((hg (f s)).mp ((hf s).mp h.2))⟩
  · intro h
    exact ⟨h.1, ((hf s).mpr ((hg (f s)).mpr h.2))⟩

theorem no_warrant_without_live
    {S : Type u} (observe : S → Prop) (s : S) :
    ¬ Warrant False observe s := by
  intro h
  exact h.1

theorem no_warrant_without_observation
    {S : Type u} (live : Prop) (s : S) :
    ¬ Warrant live (fun _ => False) s := by
  intro h
  exact h.2

theorem weakening_requires_policy_implication
    {S : Type u} (p q : Prop) (observe : S → Prop)
    (hpolicy : p → q) (s : S) :
    Warrant p observe s → Warrant q observe s := by
  intro h
  exact ⟨hpolicy h.1, h.2⟩

/-!
A live warrant is support-relative. Transport preserves the observation,
but cannot carry a warrant into a new policy without a separate proof that
the required support remains live there.
-/
def SupportedWarrant {S : Type u}
    (policy : Prop → Prop) (support : Prop)
    (observe : S → Prop) (s : S) : Prop :=
  policy support ∧ observe s

theorem supported_transport_requires_live_target
    {S : Type u} {T : Type v}
    (sourcePolicy targetPolicy : Prop → Prop)
    (support : Prop) (obsS : S → Prop) (obsT : T → Prop)
    (f : S → T)
    (preserves : ∀ s, obsS s ↔ obsT (f s))
    (policyTransfer : sourcePolicy support → targetPolicy support)
    (s : S) :
    SupportedWarrant sourcePolicy support obsS s →
      SupportedWarrant targetPolicy support obsT (f s) := by
  intro h
  exact ⟨policyTransfer h.1, (preserves s).mp h.2⟩

theorem no_target_warrant_after_revocation
    {S : Type u} (policy : Prop → Prop)
    (support : Prop) (obs : S → Prop) (s : S)
    (revoked : ¬ policy support) :
    ¬ SupportedWarrant policy support obs s := by
  intro h
  exact revoked h.1

theorem independent_alternative_support
    (supportA supportB : Prop) (obs : Prop)
    (alternative : supportB) :
    (supportA ∨ supportB) ∧ obs ↔ obs := by
  constructor
  · intro h
    exact h.2
  · intro h
    exact ⟨Or.inr alternative, h⟩


end MathGraphFoundation
