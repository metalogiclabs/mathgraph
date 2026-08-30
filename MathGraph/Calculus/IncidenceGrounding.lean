import MathGraph.Calculus.EqualityAblation

universe u w

namespace MathGraph.Calculus

/-- Bare incidence between tests and states. No outcome type, observation-value
type, comparison relation, state equality test, or apartness law is data. -/
abbrev Incidence (κ : Type w) (α : Type u) := κ → α → Prop

/-- States are observationally the same exactly when they have the same
incidence profile. -/
def IncidenceSame {κ : Type w} {α : Type u}
    (R : Incidence κ α) (x y : α) : Prop :=
  ∀ k, R k x ↔ R k y

/-- Distinction is failure of incidence-profile agreement. -/
def IncidenceDifferent {κ : Type w} {α : Type u}
    (R : Incidence κ α) (x y : α) : Prop :=
  ¬ IncidenceSame R x y

theorem incidenceSame_refl
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x : α) :
    IncidenceSame R x x := by
  intro k
  exact Iff.rfl

theorem incidenceSame_symm
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y : α}
    (h : IncidenceSame R x y) : IncidenceSame R y x := by
  intro k
  exact (h k).symm

theorem incidenceSame_trans
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y z : α}
    (hxy : IncidenceSame R x y) (hyz : IncidenceSame R y z) :
    IncidenceSame R x z := by
  intro k
  exact (hxy k).trans (hyz k)

theorem incidenceDifferent_irrefl
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x : α) :
    ¬ IncidenceDifferent R x x := by
  intro h
  exact h (incidenceSame_refl R x)

theorem incidenceDifferent_symm
    {κ : Type w} {α : Type u} {R : Incidence κ α} {x y : α}
    (h : IncidenceDifferent R x y) : IncidenceDifferent R y x := by
  intro hyx
  exact h (incidenceSame_symm hyx)

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

/-- Lawful apartness is therefore generated from incidence; its three laws are
not assumptions. -/
def incidenceLawfulSeparation
    {κ : Type w} {α : Type u} (R : Incidence κ α) :
    LawfulSeparation α :=
  { sep := IncidenceDifferent R
    irrefl := incidenceDifferent_irrefl R
    symm := incidenceDifferent_symm
    cotrans := by
      intro x z hxz y
      exact incidenceDifferent_cotrans hxz y }

/-- Only after deriving the incidence laws do we bridge back into the existing
consequence calculus. -/
def incidenceLanguage {κ : Type w} {α : Type u}
    (R : Incidence κ α) : Language κ α Prop := R

/-- Consequential identity is exactly incidence-profile agreement. The bridge
uses propositional extensionality, but the incidence construction itself did
not assume an outcome equality or comparison operation. -/
theorem incidence_identity_matches_calculus
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x y : α) :
    ConsequentialEq (incidenceLanguage R) x y ↔ IncidenceSame R x y := by
  constructor
  · intro h k
    exact Iff.of_eq (h k)
  · intro h k
    exact propext (h k)

/-- Existing language separation is exactly failure of incidence-profile
agreement. -/
theorem incidence_separation_matches_calculus
    {κ : Type w} {α : Type u} (R : Incidence κ α) (x y : α) :
    Separated (incidenceLanguage R) x y ↔ IncidenceDifferent R x y := by
  classical
  constructor
  · intro hSep hSame
    have hEq : ConsequentialEq (incidenceLanguage R) x y :=
      (incidence_identity_matches_calculus R x y).mpr hSame
    exact (consequentialEq_iff_not_separated (incidenceLanguage R) x y).mp hEq hSep
  · intro hDiff
    cases Classical.em (Separated (incidenceLanguage R) x y) with
    | inl hSep => exact hSep
    | inr hNoSep =>
        have hEq : ConsequentialEq (incidenceLanguage R) x y :=
          (consequentialEq_iff_not_separated (incidenceLanguage R) x y).mpr hNoSep
        have hSame : IncidenceSame R x y :=
          (incidence_identity_matches_calculus R x y).mp hEq
        exact False.elim (hDiff hSame)

/-- Extending the incidence universe by one test refines identity. -/
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

/-- A newly admitted incidence test that disagrees on an old-equivalent pair
forces a strict identity split. -/
theorem incidence_new_test_forces_split
    {κ : Type w} {α : Type u}
    (R : Incidence κ α) (c : α → Prop) {x y : α}
    (hOld : IncidenceSame R x y)
    (hNew : ¬ (c x ↔ c y)) :
    IncidenceSame R x y ∧ ¬ IncidenceSame (incidenceExtend R c) x y := by
  refine ⟨hOld, ?_⟩
  intro h
  exact hNew (h (Sum.inr ()))

/-- Empty incidence carries no distinctions: all states share the same empty
profile. -/
theorem empty_incidence_collapses_all
    {α : Type u} (x y : α) :
    IncidenceSame (fun k : Empty => nomatch k) x y := by
  intro k
  exact nomatch k

end MathGraph.Calculus
