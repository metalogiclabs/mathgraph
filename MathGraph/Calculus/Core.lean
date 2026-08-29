universe u v w z

namespace MathGraph.Calculus

/-- A single observable consequence of a state. -/
def Observation (α : Type u) (β : Type v) := α → β

/-- A language is an indexed family of observable consequences. -/
def Language (ι : Type w) (α : Type u) (β : Type v) :=
  ι → Observation α β

/-- Two states are identical relative to a consequence language when every
observable consequence agrees. -/
def ConsequentialEq {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (x y : α) : Prop :=
  ∀ i, L i x = L i y

@[refl] theorem consequentialEq_refl {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (x : α) : ConsequentialEq L x x := by
  intro i
  rfl

@[symm] theorem consequentialEq_symm {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {x y : α} (h : ConsequentialEq L x y) :
    ConsequentialEq L y x := by
  intro i
  exact (h i).symm

@[trans] theorem consequentialEq_trans {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {x y z : α}
    (hxy : ConsequentialEq L x y) (hyz : ConsequentialEq L y z) :
    ConsequentialEq L x z := by
  intro i
  exact (hxy i).trans (hyz i)

/-- Add one genuinely new observable to a language. -/
def extend {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) :
    Language (Sum ι Unit) α β
  | Sum.inl i => L i
  | Sum.inr _ => c

/-- Golden refinement law: extending a language by one observable refines
consequential identity by intersecting the old identity with the kernel of
that observable. -/
theorem consequentialEq_extend_iff {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) (x y : α) :
    ConsequentialEq (extend L c) x y ↔
      ConsequentialEq L x y ∧ c x = c y := by
  constructor
  · intro h
    constructor
    · intro i
      exact h (Sum.inl i)
    · exact h (Sum.inr ())
  · rintro ⟨hL, hc⟩ i
    cases i with
    | inl i => exact hL i
    | inr u => cases u; exact hc

/-- A residual witness is the minimal semantic fact that the current language
identifies two states while a candidate new consequence separates them. -/
structure ResidualWitness {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) (x y : α) : Prop where
  indistinguishable : ConsequentialEq L x y
  separated : c x ≠ c y

/-- A residual witness certifies that the extended language must split the two
previously identified states. -/
theorem residual_forces_split {ι : Type w} {α : Type u} {β : Type v}
    {L : Language ι α β} {c : Observation α β} {x y : α}
    (r : ResidualWitness L c x y) :
    ¬ ConsequentialEq (extend L c) x y := by
  intro h
  have hc : c x = c y := (consequentialEq_extend_iff L c x y).mp h |>.2
  exact r.separated hc

/-- Postcomposition changes the codomain of observations without creating a
new distinction between states already identified by the source language. -/
def postcompose {ι : Type w} {α : Type u} {β : Type v} {γ : Type z}
    (f : β → γ) (L : Language ι α β) : Language ι α γ :=
  fun i x => f (L i x)

theorem consequentialEq_postcompose {ι : Type w} {α : Type u}
    {β : Type v} {γ : Type z} (f : β → γ) (L : Language ι α β)
    {x y : α} (h : ConsequentialEq L x y) :
    ConsequentialEq (postcompose f L) x y := by
  intro i
  exact congrArg f (h i)

/-- Reindexing selects/reorders existing observables and therefore cannot
separate states that the original language identified. -/
def reindex {ι : Type w} {κ : Type z} {α : Type u} {β : Type v}
    (f : κ → ι) (L : Language ι α β) : Language κ α β :=
  fun k => L (f k)

theorem consequentialEq_reindex {ι : Type w} {κ : Type z} {α : Type u}
    {β : Type v} (f : κ → ι) (L : Language ι α β)
    {x y : α} (h : ConsequentialEq L x y) :
    ConsequentialEq (reindex f L) x y := by
  intro k
  exact h (f k)

/-- A candidate consequence is redundant exactly when it never separates a
pair already identified by the current language. -/
def Redundant {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) : Prop :=
  ∀ ⦃x y⦄, ConsequentialEq L x y → c x = c y

/-- Redundancy is equivalent to saying that adding the candidate consequence
leaves consequential identity unchanged. -/
theorem redundant_iff_extension_conservative
    {ι : Type w} {α : Type u} {β : Type v}
    (L : Language ι α β) (c : Observation α β) :
    Redundant L c ↔
      ∀ x y, ConsequentialEq (extend L c) x y ↔ ConsequentialEq L x y := by
  constructor
  · intro hred x y
    constructor
    · intro hext
      exact (consequentialEq_extend_iff L c x y).mp hext |>.1
    · intro hL
      exact (consequentialEq_extend_iff L c x y).mpr ⟨hL, hred hL⟩
  · intro h x y hL
    have hext : ConsequentialEq (extend L c) x y := (h x y).mpr hL
    exact (consequentialEq_extend_iff L c x y).mp hext |>.2

end MathGraph.Calculus
