import MathGraph.Calculus.Representation

universe u v w

namespace MathGraph.Calculus

/-- A completely raw experiment family: an index chooses an experiment and the
experiment returns an outcome.  There are no laws on experiments or states. -/
abbrev RawExperiment (ι : Type w) (α : Type u) (β : Type v) := ι → α → β

/-- State separation generated only by unequal experimental outcomes. -/
def OutcomeSeparated {ι : Type w} {α : Type u} {β : Type v}
    (E : RawExperiment ι α β) (x y : α) : Prop :=
  ∃ i, E i x ≠ E i y

/-- No state-level irreflexivity axiom is assumed: it follows from equality of
an outcome with itself. -/
theorem outcomeSeparated_irrefl
    {ι : Type w} {α : Type u} {β : Type v}
    (E : RawExperiment ι α β) (x : α) :
    ¬ OutcomeSeparated E x x := by
  intro h
  rcases h with ⟨i, hne⟩
  exact hne rfl

/-- No state-level symmetry axiom is assumed: it follows from symmetry of
outcome equality. -/
theorem outcomeSeparated_symm
    {ι : Type w} {α : Type u} {β : Type v}
    {E : RawExperiment ι α β} {x y : α}
    (h : OutcomeSeparated E x y) : OutcomeSeparated E y x := by
  rcases h with ⟨i, hne⟩
  exact ⟨i, fun hEq => hne hEq.symm⟩

/-- No state-level cotransitivity axiom is assumed.  For a witnessing experiment,
either the first two outcomes differ or equality of those two transfers the
original difference to the second pair. -/
theorem outcomeSeparated_cotrans
    {ι : Type w} {α : Type u} {β : Type v}
    {E : RawExperiment ι α β} {x y z : α}
    (h : OutcomeSeparated E x z) :
    OutcomeSeparated E x y ∨ OutcomeSeparated E y z := by
  rcases h with ⟨i, hxz⟩
  classical
  cases Classical.em (E i x = E i y) with
  | inl hxy =>
      right
      refine ⟨i, ?_⟩
      intro hyz
      exact hxz (hxy.trans hyz)
  | inr hxy =>
      left
      exact ⟨i, hxy⟩

/-- Therefore every raw experiment family, with ordinary equality as the only
outcome comparator, generates a lawful state separation. -/
def outcomeLawfulSeparation
    {ι : Type w} {α : Type u} {β : Type v}
    (E : RawExperiment ι α β) : LawfulSeparation α :=
  { sep := OutcomeSeparated E
    irrefl := outcomeSeparated_irrefl E
    symm := outcomeSeparated_symm
    cotrans := by
      intro x z h y
      exact outcomeSeparated_cotrans (E := E) (x := x) (y := y) (z := z) h }

/-- The generated relation is exactly the existing consequence-language
separation.  `RawExperiment` adds no hidden semantic assumption. -/
theorem outcomeSeparated_eq_languageSeparated
    {ι : Type w} {α : Type u} {β : Type v}
    (E : RawExperiment ι α β) (x y : α) :
    OutcomeSeparated E x y ↔ Separated E x y := by
  rfl

/-- Now ablate equality-as-comparator.  An arbitrary primitive outcome
`different` relation need not generate a lawful state separation. -/
def RelSeparated {ι : Type w} {α : Type u} {β : Type v}
    (different : β → β → Prop) (E : RawExperiment ι α β)
    (x y : α) : Prop :=
  ∃ i, different (E i x) (E i y)

/-- The exact laws required of an arbitrary outcome discriminator. -/
structure LawfulOutcomeDifference (β : Type v) where
  different : β → β → Prop
  irrefl : ∀ b, ¬ different b b
  symm : ∀ {a b}, different a b → different b a
  cotrans : ∀ {a c}, different a c → ∀ b, different a b ∨ different b c

/-- Lawfulness at the outcome level lifts to state separation for every raw
experiment family. -/
theorem lawfulOutcomeDifference_lifts
    {ι : Type w} {α : Type u} {β : Type v}
    (D : LawfulOutcomeDifference β) (E : RawExperiment ι α β) :
    (∀ x, ¬ RelSeparated D.different E x x) ∧
    (∀ {x y}, RelSeparated D.different E x y → RelSeparated D.different E y x) ∧
    (∀ {x z}, RelSeparated D.different E x z → ∀ y,
      RelSeparated D.different E x y ∨ RelSeparated D.different E y z) := by
  constructor
  · intro x h
    rcases h with ⟨i, hbad⟩
    exact D.irrefl (E i x) hbad
  constructor
  · intro x y h
    rcases h with ⟨i, hxy⟩
    exact ⟨i, D.symm hxy⟩
  · intro x z h y
    rcases h with ⟨i, hxz⟩
    cases D.cotrans hxz (E i y) with
    | inl hxy => exact Or.inl ⟨i, hxy⟩
    | inr hyz => exact Or.inr ⟨i, hyz⟩

/-- Conversely, if an outcome discriminator generates lawful separation for
*every* experiment family, then the discriminator itself must be lawful.  Use
the one-experiment identity experiment, so generated state separation is
literally the outcome discriminator. -/
def universal_lift_forces_outcome_laws
    {β : Type v} (different : β → β → Prop)
    (hAll : ∀ (E : RawExperiment Unit β β),
      (∀ x, ¬ RelSeparated different E x x) ∧
      (∀ {x y}, RelSeparated different E x y → RelSeparated different E y x) ∧
      (∀ {x z}, RelSeparated different E x z → ∀ y,
        RelSeparated different E x y ∨ RelSeparated different E y z)) :
    LawfulOutcomeDifference β := by
  let ident : RawExperiment Unit β β := fun _ x => x
  have h := hAll ident
  refine {
    different := different
    irrefl := ?_
    symm := ?_
    cotrans := ?_
  }
  · intro b hbb
    exact h.1 b ⟨(), hbb⟩
  · intro a b hab
    rcases h.2.1 ⟨(), hab⟩ with ⟨u, hba⟩
    exact hba
  · intro a c hac b
    cases h.2.2 ⟨(), hac⟩ b with
    | inl hab =>
        rcases hab with ⟨u, hab'⟩
        exact Or.inl hab'
    | inr hbc =>
        rcases hbc with ⟨u, hbc'⟩
        exact Or.inr hbc'

/-- Ordinary inequality is a lawful outcome discriminator; its laws are not
assumptions about state separation but consequences of equality. -/
def inequalityOutcomeDifference (β : Type v) : LawfulOutcomeDifference β :=
  { different := fun a b => a ≠ b
    irrefl := fun b h => h rfl
    symm := fun h hEq => h hEq.symm
    cotrans := by
      intro a c hac b
      classical
      cases Classical.em (a = b) with
      | inl hab =>
          right
          intro hbc
          exact hac (hab.trans hbc)
      | inr hab => exact Or.inl hab }

/-- Exact foundation decision: state-level apartness laws need not be assumed.
They are generated by raw experiments once outcome difference is ordinary
inequality.  If outcome difference itself is left completely arbitrary, the
same three laws are exactly what is required for universal lifting. -/
def no_state_apartness_axioms_needed
    {ι : Type w} {α : Type u} {β : Type v}
    (E : RawExperiment ι α β) :
    LawfulSeparation α :=
  outcomeLawfulSeparation E

end MathGraph.Calculus
