/-!
MathGraph general proof calculus.
No axioms, sorry, external IO, or source-admission shortcuts.
Theorems quantify over arbitrary proposition types and finite derivation trees.
External evidence authentication remains an explicit premise.
-/
universe u v

namespace MathGraphFoundation

inductive Derives {Claim : Type u}
    (Evidence : Claim → Prop) (Rule : Claim → List Claim → Prop) :
    Claim → Prop where
  | evidence {c : Claim} : Evidence c → Derives Evidence Rule c
  | inference {c : Claim} {premises : List Claim} :
      Rule c premises →
      (∀ p, p ∈ premises → Derives Evidence Rule p) →
      Derives Evidence Rule c

theorem derivation_has_authorized_origin
    {Claim : Type u}
    (Evidence : Claim → Prop) (Rule : Claim → List Claim → Prop)
    (origin : Claim → Prop)
    (he : ∀ c, Evidence c → origin c)
    (hr : ∀ c ps, Rule c ps →
      (∀ p, p ∈ ps → origin p) → origin c)
    {c : Claim} (d : Derives Evidence Rule c) : origin c := by
  induction d with
  | evidence h => exact he _ h
  | inference rule premises ih =>
      exact hr _ _ rule (fun p hp => ih p hp)

theorem evidence_monotonicity
    {Claim : Type u}
    (E F : Claim → Prop) (Rule : Claim → List Claim → Prop)
    (incl : ∀ c, E c → F c)
    {c : Claim} (d : Derives E Rule c) :
    Derives F Rule c := by
  induction d with
  | evidence h => exact .evidence (incl _ h)
  | inference rule premises ih =>
      exact .inference rule (fun p hp => ih p hp)

theorem alternative_support_survives
    {Claim : Type u} (E : Claim → Prop)
    (Rule : Claim → List Claim → Prop)
    (a b target : Claim)
    (hb : E b) (r : Rule target [b]) :
    Derives E Rule target := by
  apply Derives.inference r
  intro p hp
  have h : p = b := by
    simp only [List.mem_cons, List.not_mem_nil, or_false] at hp
    exact hp
  subst p
  exact Derives.evidence hb

theorem unsupported_cycle_cannot_self_certify
    {Claim : Type u}
    (E : Claim → Prop) (Rule : Claim → List Claim → Prop)
    (origin : Claim → Prop)
    (he : ∀ c, E c → origin c)
    (hr : ∀ c ps, Rule c ps →
      (∀ p, p ∈ ps → origin p) → origin c)
    (c : Claim) (noOrigin : ¬ origin c) :
    ¬ Derives E Rule c := by
  intro d
  exact noOrigin (derivation_has_authorized_origin E Rule origin he hr d)

inductive Trace {State : Type u} (Step : State → State → Prop) :
    State → State → Prop where
  | refl (s : State) : Trace Step s s
  | next {a b c : State} :
      Step a b → Trace Step b c → Trace Step a c

theorem invariant_over_trace
    {State : Type u}
    (Step : State → State → Prop)
    (Safe : State → Prop)
    (preserve : ∀ a b, Step a b → Safe a → Safe b)
    {a b : State}
    (path : Trace Step a b) (initial : Safe a) : Safe b := by
  induction path with
  | refl s => exact initial
  | next h tail ih => exact ih (preserve _ _ h initial)

def Admitted {State : Type u}
    (Authorized Supported : State → State → Prop)
    (Safe : State → Prop) (a b : State) : Prop :=
  Authorized a b ∧ Supported a b ∧ Safe b

theorem admitted_requires_authorization
    {State : Type u}
    (Authorized Supported : State → State → Prop)
    (Safe : State → Prop) (a b : State)
    (h : Admitted Authorized Supported Safe a b) :
    Authorized a b := h.1

theorem admitted_requires_live_support
    {State : Type u}
    (Authorized Supported : State → State → Prop)
    (Safe : State → Prop) (a b : State)
    (h : Admitted Authorized Supported Safe a b) :
    Supported a b := h.2.1

theorem admitted_preserves_safe_successor
    {State : Type u}
    (Authorized Supported : State → State → Prop)
    (Safe : State → Prop) (a b : State)
    (h : Admitted Authorized Supported Safe a b) :
    Safe b := h.2.2

end MathGraphFoundation
