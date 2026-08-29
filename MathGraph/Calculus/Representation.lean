import MathGraph.Calculus.Separation

universe u

namespace MathGraph.Calculus

/-- An abstract lawful separation relation.  These are exactly the relation laws
used in the MSI primitive-ablation layer: irreflexivity, symmetry, and
cotransitivity. -/
structure LawfulSeparation (α : Type u) where
  sep : α → α → Prop
  irrefl : ∀ x, ¬ sep x x
  symm : ∀ {x y}, sep x y → sep y x
  cotrans : ∀ {x z}, sep x z → ∀ y, sep x y ∨ sep y z

/-- The canonical consequence language represented by a lawful separation.
Each state `i` becomes an observation asking which states are separated from
`i`. -/
def LawfulSeparation.language {α : Type u} (S : LawfulSeparation α) :
    Language α α Prop :=
  fun i x => S.sep i x

/-- Every abstract lawful separation is represented exactly by the separation
relation induced by its canonical consequence language. -/
theorem lawfulSeparation_represented
    {α : Type u} (S : LawfulSeparation α) (x y : α) :
    Separated S.language x y ↔ S.sep x y := by
  classical
  constructor
  · rintro ⟨i, hdiff⟩
    by_cases hix : S.sep i x
    · by_cases hiy : S.sep i y
      · exact False.elim (hdiff (propext ⟨fun _ => hiy, fun _ => hix⟩))
      · cases S.cotrans hix y with
        | inl hiy' => exact False.elim (hiy hiy')
        | inr hyx => exact S.symm hyx
    · by_cases hiy : S.sep i y
      · cases S.cotrans hiy x with
        | inl hix' => exact False.elim (hix hix')
        | inr hxy => exact hxy
      · exact False.elim (hdiff (propext ⟨fun h => False.elim (hix h), fun h => False.elim (hiy h)⟩))
  · intro hxy
    refine ⟨x, ?_⟩
    intro hEq
    have hxx : S.sep x x := hEq ▸ hxy
    exact S.irrefl x hxx

/-- Consequently, the abstract identity induced by non-separation is exactly
consequential identity in the canonical language. -/
theorem lawfulSeparation_identity_is_consequential
    {α : Type u} (S : LawfulSeparation α) (x y : α) :
    (¬ S.sep x y) ↔ ConsequentialEq S.language x y := by
  rw [consequentialEq_iff_not_separated]
  exact not_congr (lawfulSeparation_represented S x y)

/-- The consequence/separation construction is therefore surjective onto all
lawful separation relations: no additional representability axiom is needed
for this abstract static layer. -/
theorem every_lawful_separation_has_consequence_representation
    {α : Type u} (S : LawfulSeparation α) :
    ∃ (L : Language α α Prop), ∀ x y,
      Separated L x y ↔ S.sep x y := by
  exact ⟨S.language, lawfulSeparation_represented S⟩

end MathGraph.Calculus
