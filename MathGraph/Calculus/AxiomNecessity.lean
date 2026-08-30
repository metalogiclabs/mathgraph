import MathGraph.Calculus.Representation

universe u

namespace MathGraph.Calculus

/-- The three relation laws forced by consequence-induced separation. -/
def LawfulRelation {α : Type u} (R : α → α → Prop) : Prop :=
  (∀ x, ¬ R x x) ∧
  (∀ {x y}, R x y → R y x) ∧
  (∀ {x z}, R x z → ∀ y, R x y ∨ R y z)

/-- Exact representability by the canonical consequence-language shape used in
this calculus. -/
def Representable {α : Type u} (R : α → α → Prop) : Prop :=
  ∃ (L : Language α α Prop), ∀ x y, Separated L x y ↔ R x y

/-- Any exactly consequence-representable relation is irreflexive. -/
theorem representable_implies_irrefl
    {α : Type u} {R : α → α → Prop}
    (hR : Representable R) : ∀ x, ¬ R x x := by
  rcases hR with ⟨L, h⟩
  intro x hxx
  exact separated_irrefl L x ((h x x).mpr hxx)

/-- Any exactly consequence-representable relation is symmetric. -/
theorem representable_implies_symm
    {α : Type u} {R : α → α → Prop}
    (hR : Representable R) : ∀ {x y}, R x y → R y x := by
  rcases hR with ⟨L, h⟩
  intro x y hxy
  have hs : Separated L x y := (h x y).mpr hxy
  exact (h y x).mp (separated_symm hs)

/-- Any exactly consequence-representable relation is cotransitive. -/
theorem representable_implies_cotrans
    {α : Type u} {R : α → α → Prop}
    (hR : Representable R) :
    ∀ {x z}, R x z → ∀ y, R x y ∨ R y z := by
  rcases hR with ⟨L, h⟩
  intro x z hxz y
  have hs : Separated L x z := (h x z).mpr hxz
  cases separated_cotrans hs with
  | inl hxy => exact Or.inl ((h x y).mp hxy)
  | inr hyz => exact Or.inr ((h y z).mp hyz)

/-- Exact consequence representability forces all three laws. -/
theorem representable_implies_lawful
    {α : Type u} {R : α → α → Prop}
    (hR : Representable R) : LawfulRelation R := by
  exact ⟨representable_implies_irrefl hR,
    representable_implies_symm hR,
    representable_implies_cotrans hR⟩

/-- Conversely, the three laws are sufficient: the canonical Prop-valued
language from `Representation.lean` represents the relation exactly. -/
theorem lawful_implies_representable
    {α : Type u} {R : α → α → Prop}
    (hLaw : LawfulRelation R) : Representable R := by
  rcases hLaw with ⟨hirr, hsymm, hcotrans⟩
  let S : LawfulSeparation α := {
    sep := R
    irrefl := hirr
    symm := hsymm
    cotrans := hcotrans
  }
  exact ⟨S.language, lawfulSeparation_represented S⟩

/-- Exact characterization: a binary relation is representable as separation
by a consequence language iff it is irreflexive, symmetric, and cotransitive.
Thus none of these laws is dispensable from the exact static representation
class unless it follows from the others. -/
theorem representable_iff_lawful
    {α : Type u} (R : α → α → Prop) :
    Representable R ↔ LawfulRelation R := by
  constructor
  · exact representable_implies_lawful
  · exact lawful_implies_representable

end MathGraph.Calculus
