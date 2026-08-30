import MathGraph.Calculus.EqualityAblation

universe u w

namespace MathGraph.Calculus

/-- The lowest substrate tested here: a bare incidence relation between tests
and states. There is no outcome type, observation-value type, comparison
relation, state equality test, or apartness law in the data. -/
abbrev Incidence (κ : Type w) (α : Type u) := κ → α → Prop

/-- Two states have the same incidence profile when every test holds of one
exactly when it holds of the other. This is derived from the bare relation. -/
def IncidenceSame {κ : Type w} {α : Type u}
    (R : Incidence κ α) (x y : α) : Prop :=
  ∀ k, R k x ↔ R k y

/-- Distinction is failure of incidence-profile agreement. No primitive
state-separation relation is supplied. -/
def IncidenceDifferent {κ : Type w} {α : Type u}
    (R : Incidence κ α) (x y : α) : Prop :=
  ¬ IncidenceSame R x y

/-- Incidence-profile sameness is reflexive without any state-level axiom. -/
theorem incidenceSame_refl
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x : α) :
    IncidenceSame R x x := by
  intro k
  exact Iff.rfl

/-- Incidence-profile sameness is symmetric without any state-level axiom. -/
theorem incidenceSame_symm
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y : α}
    (h : IncidenceSame R x y) : IncidenceSame R y x := by
  intro k
  exact (h k).symm

/-- Incidence-profile sameness is transitive without any state-level axiom. -/
theorem incidenceSame_trans
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y z : α}
    (hxy : IncidenceSame R x y) (hyz : IncidenceSame R y z) :
    IncidenceSame R x z := by
  intro k
  exact (hxy k).trans (hyz k)

/-- The induced distinction is irreflexive. -/
theorem incidenceDifferent_irrefl
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x : α) :
    ¬ IncidenceDifferent R x x := by
  intro h
  exact h (incidenceSame_refl R x)

/-- The induced distinction is symmetric. -/
theorem incidenceDifferent_symm
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y : α}
    (h : IncidenceDifferent R x y) : IncidenceDifferent R y x := by
  intro hyx
  exact h (incidenceSame_symm hyx)

/-- The induced distinction is cotransitive. -/
theorem incidenceDifferent_cotrans
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x z : α}
    (h : IncidenceDifferent R x z) (y : α) :
    IncidenceDifferent R x y ∨ IncidenceDifferent R y z := by
  classical
  cases Classical.em (IncidenceSame R x y) with
  | inl hxy =>
      right
      intro hyz
      exact h (incidenceSame_trans hxy hyz)
  | inr hxy => exact Or.inl hxy

/-- Bare incidence therefore generates a lawful separation relation. -/
def incidenceLawfulSeparation
    {κ : Type w} {α : Type u} (R : Incidence κ α) :
    LawfulSeparation α :=
  { sep := IncidenceDifferent R
    irrefl := incidenceDifferent_irrefl R
    symm := incidenceDifferent_symm
    cotrans := by
      intro x z hxz y
      exact incidenceDifferent_cotrans hxz y }

/-- A direct witness form of distinction: under classical logic, profile
failure means some test has opposite incidence on the two states. -/
theorem incidenceDifferent_iff_witness
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x y : α) :
    IncidenceDifferent R x y ↔
      ∃ k, (R k x ∧ ¬ R k y) ∨ (¬ R k x ∧ R k y) := by
  classical
  constructor
  · intro h
    by_contra hnone
    apply h
    intro k
    constructor
    · intro hx
      by_contra hny
      apply hnone
      exact ⟨k, Or.inl ⟨hx, hny⟩⟩
    · intro hy
      by_contra hnx
      apply hnone
      exact ⟨k, Or.inr ⟨hnx, hy⟩⟩
  · rintro ⟨k, h⟩ hsame
    cases h with
    | inl hxy => exact hxy.2 ((hsame k).mp hxy.1)
    | inr hyx => exact hyx.1 ((hsame k).mpr hyx.2)

/-- The bare incidence relation can be viewed as a consequence language only
after the foundational laws have already been derived. This is a bridge, not
an assumption of the construction. -/
def incidenceLanguage {κ : Type w} {α : Type u}
    (R : Incidence κ α) : Language κ α Prop := R

/-- Existing consequence separation is exactly incidence distinction. -/
theorem incidence_separation_matches_calculus
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x y : α) :
    Separated (incidenceLanguage R) x y ↔ IncidenceDifferent R x y := by
  classical
  rw [incidenceDifferent_iff_witness]
  constructor
  · rintro ⟨k, hne⟩
    cases Classical.em (R k x) with
    | inl hx =>
        have hny : ¬ R k y := by
          intro hy
          exact hne (propext ⟨fun _ => hy, fun _ => hx⟩)
        exact ⟨k, Or.inl ⟨hx, hny⟩⟩
    | inr hnx =>
        have hy : R k y := by
          by_contra hny
          exact hne (propext ⟨fun h => False.elim (hnx h), fun h => False.elim (hny h)⟩)
        exact ⟨k, Or.inr ⟨hnx, hy⟩⟩
  · rintro ⟨k, h⟩
    refine ⟨k, ?_⟩
    cases h with
    | inl hxy =>
        intro heq
        exact hxy.2 (Eq.mp heq hxy.1)
    | inr hyx =>
        intro heq
        exact hyx.1 (Eq.mpr heq hyx.2)

/-- Consequently the existing consequential identity is exactly agreement of
incidence profiles. -/
theorem incidence_identity_matches_calculus
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x y : α) :
    ConsequentialEq (incidenceLanguage R) x y ↔ IncidenceSame R x y := by
  rfl

/-- Extending the raw incidence universe by one new test refines identity
without needing outcomes or an independently postulated separation law. -/
def incidenceExtend {κ : Type w} {α : Type u}
    (R : Incidence κ α) (c : α → Prop) : Incidence (Sum κ Unit) α
  | Sum.inl k, x => R k x
  | Sum.inr _, x => c x

theorem incidence_extension_refines
    {κ : Type w} {α : Type u}
    (R : Incidence κ α) (c : α → Prop) {x y : α}
    (h : IncidenceSame (incidenceExtend R c) x y) :
    IncidenceSame R x y := by
  intro k
  exact h (Sum.inl k)

/-- A new incidence test that disagrees on an old-equivalent pair forces a
strict split. -/
theorem incidence_new_test_forces_split
    {κ : Type w} {α : Type u}
    (R : Incidence κ α) (c : α → Prop) {x y : α}
    (hOld : IncidenceSame R x y)
    (hNew : ¬ (c x ↔ c y)) :
    IncidenceSame R x y ∧ ¬ IncidenceSame (incidenceExtend R c) x y := by
  refine ⟨hOld, ?_⟩
  intro h
  exact hNew (h (Sum.inr ()))

/-- With no tests there are no justified distinctions: every pair has the same
empty incidence profile. -/
theorem empty_incidence_collapses_all
    {α : Type u} (x y : α) :
    IncidenceSame (fun k : Empty => nomatch k) x y := by
  intro k
  exact nomatch k

end MathGraph.Calculus
