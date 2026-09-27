namespace VerifiedDevelopmentalNavigation

/-!
# Protected action quotients

A domain-independent pruning theorem for Crystal-style action compression.

The theorem does not assume chess, numerical scores, or a particular ordering.
A representative set is safe exactly when it realizes every protected outcome
realized by the full action set, while containing only legal actions.

Consequently every predicate over protected outcomes is preserved. In
particular, any optimum/minimax decision whose comparison depends only on the
protected outcome may be computed over one representative per outcome class.
-/

namespace ActionQuotient

variable {A V : Type}

/-- A protected outcome is realizable by an action list. -/
def OutcomeReachable (actions : List A) (value : A → V) (v : V) : Prop :=
  ∃ a, a ∈ actions ∧ value a = v

/-- Representatives contain only actions admitted by the original action set. -/
def SoundRepresentatives (actions reps : List A) : Prop :=
  ∀ ⦃r⦄, r ∈ reps → r ∈ actions

/-- Every protected outcome of the full action set has a representative. -/
def OutcomeComplete
    (actions reps : List A) (value : A → V) : Prop :=
  ∀ ⦃a⦄, a ∈ actions → ∃ r, r ∈ reps ∧ value r = value a

/-- Sound and outcome-complete representatives realize exactly the same
protected outcome set as the full legal action list. -/
theorem outcomeReachable_iff
    (actions reps : List A) (value : A → V)
    (hsound : SoundRepresentatives actions reps)
    (hcomplete : OutcomeComplete actions reps value)
    (v : V) :
    OutcomeReachable actions value v ↔ OutcomeReachable reps value v := by
  constructor
  · intro h
    rcases h with ⟨a, ha, hav⟩
    rcases hcomplete ha with ⟨r, hr, hra⟩
    exact ⟨r, hr, hra.trans hav⟩
  · intro h
    rcases h with ⟨r, hr, hrv⟩
    exact ⟨r, hsound hr, hrv⟩

/-- Every verifier-visible predicate over protected outcomes is invariant under
outcome-complete representative pruning. -/
theorem exists_predicate_iff
    (actions reps : List A) (value : A → V)
    (hsound : SoundRepresentatives actions reps)
    (hcomplete : OutcomeComplete actions reps value)
    (P : V → Prop) :
    (∃ a, a ∈ actions ∧ P (value a)) ↔
      (∃ r, r ∈ reps ∧ P (value r)) := by
  constructor
  · intro h
    rcases h with ⟨a, ha, hPa⟩
    rcases hcomplete ha with ⟨r, hr, hra⟩
    have hPr : P (value r) := by
      simpa [hra] using hPa
    exact ⟨r, hr, hPr⟩
  · intro h
    rcases h with ⟨r, hr, hPr⟩
    exact ⟨r, hsound hr, hPr⟩

/-- best is optimal relative to an arbitrary strict preference relation when
it is realizable and no realizable protected outcome is strictly preferred. -/
def IsOptimal
    (actions : List A) (value : A → V)
    (better : V → V → Prop) (best : V) : Prop :=
  OutcomeReachable actions value best ∧
    ∀ v, OutcomeReachable actions value v → ¬ better v best

/-- Outcome-complete action quotienting preserves every optimum defined solely
from the protected outcome and an arbitrary preference relation.

For chess, instantiate V with the protected WDL/DTZ consequence and better
with the side-to-move preference. The result justifies deleting all but one
representative from each consequence-pure action class without changing the
minimax choice at that node. -/
theorem isOptimal_iff
    (actions reps : List A) (value : A → V)
    (hsound : SoundRepresentatives actions reps)
    (hcomplete : OutcomeComplete actions reps value)
    (better : V → V → Prop) (best : V) :
    IsOptimal actions value better best ↔
      IsOptimal reps value better best := by
  constructor
  · intro h
    rcases h with ⟨hreach, hbest⟩
    constructor
    · exact (outcomeReachable_iff actions reps value hsound hcomplete best).mp hreach
    · intro v hv
      exact hbest v
        ((outcomeReachable_iff actions reps value hsound hcomplete v).mpr hv)
  · intro h
    rcases h with ⟨hreach, hbest⟩
    constructor
    · exact (outcomeReachable_iff actions reps value hsound hcomplete best).mpr hreach
    · intro v hv
      exact hbest v
        ((outcomeReachable_iff actions reps value hsound hcomplete v).mp hv)

/-- If a quotient key is consequence-pure inside one legal action set,
choosing one legal representative for every realized key is outcome-complete.

This is the bridge used by Crystal Chess: learned schemas provide the key,
external exact verification establishes key purity, and the theorem above
licenses representative pruning. -/
theorem outcomeComplete_of_key_pure
    {K : Type}
    (actions reps : List A) (value : A → V) (key : A → K)
    (hsound : SoundRepresentatives actions reps)
    (hrep : ∀ ⦃a⦄, a ∈ actions → ∃ r, r ∈ reps ∧ key r = key a)
    (hpure :
      ∀ ⦃a b⦄, a ∈ actions → b ∈ actions →
        key a = key b → value a = value b) :
    OutcomeComplete actions reps value := by
  intro a ha
  rcases hrep ha with ⟨r, hr, hkey⟩
  have hrActions : r ∈ actions := hsound hr
  exact ⟨r, hr, hpure hrActions ha hkey⟩

end ActionQuotient

end VerifiedDevelopmentalNavigation
