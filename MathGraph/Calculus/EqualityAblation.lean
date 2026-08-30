import MathGraph.Calculus.OutcomeGrounding

universe u v w q

namespace MathGraph.Calculus

/-- A raw family of proposition-valued tests on outcomes.  No equality or
comparison relation on the outcome type is supplied. -/
abbrev OutcomeTests (κ : Type q) (β : Type v) := κ → β → Prop

/-- Two outcomes are observationally the same when every raw test has the same
truth value on them.  This does not use equality on `β`. -/
def TestEquivalent {κ : Type q} {β : Type v}
    (T : OutcomeTests κ β) (a b : β) : Prop :=
  ∀ k, T k a ↔ T k b

/-- Outcome difference is generated as failure of test-equivalence, rather than
being supplied as primitive equality/inequality on outcomes. -/
def TestDifferent {κ : Type q} {β : Type v}
    (T : OutcomeTests κ β) (a b : β) : Prop :=
  ¬ TestEquivalent T a b

theorem testEquivalent_refl
    {κ : Type q} {β : Type v} (T : OutcomeTests κ β) (a : β) :
    TestEquivalent T a a := by
  intro k
  exact Iff.rfl

theorem testEquivalent_symm
    {κ : Type q} {β : Type v} {T : OutcomeTests κ β} {a b : β}
    (h : TestEquivalent T a b) : TestEquivalent T b a := by
  intro k
  exact (h k).symm

theorem testEquivalent_trans
    {κ : Type q} {β : Type v} {T : OutcomeTests κ β} {a b c : β}
    (hab : TestEquivalent T a b) (hbc : TestEquivalent T b c) :
    TestEquivalent T a c := by
  intro k
  exact (hab k).trans (hbc k)

/-- Irreflexivity of generated difference is derived; it is not assumed. -/
theorem testDifferent_irrefl
    {κ : Type q} {β : Type v} (T : OutcomeTests κ β) (a : β) :
    ¬ TestDifferent T a a := by
  intro h
  exact h (testEquivalent_refl T a)

/-- Symmetry of generated difference is derived from symmetry of logical
biconditional across the raw tests. -/
theorem testDifferent_symm
    {κ : Type q} {β : Type v} {T : OutcomeTests κ β} {a b : β}
    (h : TestDifferent T a b) : TestDifferent T b a := by
  intro hba
  exact h (testEquivalent_symm hba)

/-- Cotransitivity of generated difference is derived from transitivity of
agreement across tests. -/
theorem testDifferent_cotrans
    {κ : Type q} {β : Type v} {T : OutcomeTests κ β} {a c : β}
    (h : TestDifferent T a c) (b : β) :
    TestDifferent T a b ∨ TestDifferent T b c := by
  classical
  cases Classical.em (TestEquivalent T a b) with
  | inl hab =>
      right
      intro hbc
      exact h (testEquivalent_trans hab hbc)
  | inr hab =>
      left
      exact hab

/-- Thus raw tests themselves generate a lawful outcome discriminator. -/
def testGeneratedOutcomeDifference
    {κ : Type q} {β : Type v} (T : OutcomeTests κ β) :
    LawfulOutcomeDifference β :=
  { different := TestDifferent T
    irrefl := testDifferent_irrefl T
    symm := testDifferent_symm
    cotrans := by
      intro a c hac b
      exact testDifferent_cotrans hac b }

/-- A raw experiment family observed through raw outcome tests. -/
def TestSeparated
    {κ : Type q} {ι : Type w} {α : Type u} {β : Type v}
    (T : OutcomeTests κ β) (E : RawExperiment ι α β)
    (x y : α) : Prop :=
  ∃ i, TestDifferent T (E i x) (E i y)

/-- The state apartness laws are now generated with no state-level laws and no
outcome equality relation supplied. -/
def testGeneratedStateSeparation
    {κ : Type q} {ι : Type w} {α : Type u} {β : Type v}
    (T : OutcomeTests κ β) (E : RawExperiment ι α β) :
    LawfulSeparation α :=
  { sep := TestSeparated T E
    irrefl := by
      intro x h
      rcases h with ⟨i, hbad⟩
      exact testDifferent_irrefl T (E i x) hbad
    symm := by
      intro x y h
      rcases h with ⟨i, hxy⟩
      exact ⟨i, testDifferent_symm hxy⟩
    cotrans := by
      intro x z hxz y
      rcases hxz with ⟨i, hxz'⟩
      cases testDifferent_cotrans hxz' (E i y) with
      | inl hxy => exact Or.inl ⟨i, hxy⟩
      | inr hyz => exact Or.inr ⟨i, hyz⟩ }

/-- State identity can be defined directly as agreement on every test after
every experiment, again without equality on outcomes. -/
def TestConsequentialEq
    {κ : Type q} {ι : Type w} {α : Type u} {β : Type v}
    (T : OutcomeTests κ β) (E : RawExperiment ι α β)
    (x y : α) : Prop :=
  ∀ i k, T k (E i x) ↔ T k (E i y)

/-- Generated consequential identity is exactly non-separation. -/
theorem testConsequentialEq_iff_not_separated
    {κ : Type q} {ι : Type w} {α : Type u} {β : Type v}
    (T : OutcomeTests κ β) (E : RawExperiment ι α β) (x y : α) :
    TestConsequentialEq T E x y ↔ ¬ TestSeparated T E x y := by
  classical
  constructor
  · intro hEq hSep
    rcases hSep with ⟨i, hDiff⟩
    apply hDiff
    intro k
    exact hEq i k
  · intro hNoSep i k
    cases Classical.em (T k (E i x) ↔ T k (E i y)) with
    | inl h => exact h
    | inr h =>
        exfalso
        apply hNoSep
        refine ⟨i, ?_⟩
        intro hAll
        exact h (hAll k)

/-- The already-verified consequence-language representation theorem now
applies to a structure generated without semantic equality on the outcome type. -/
theorem raw_tests_generate_consequence_representation
    {κ : Type q} {ι : Type w} {α : Type u} {β : Type v}
    (T : OutcomeTests κ β) (E : RawExperiment ι α β) :
    ∃ (L : Language α α Prop), ∀ x y,
      Separated L x y ↔ TestSeparated T E x y := by
  exact every_lawful_separation_has_consequence_representation
    (testGeneratedStateSeparation T E)

/-- With no tests at all, no outcome distinction can be justified.  The bottom
case is maximal observational identification, not an assumed equality. -/
theorem no_tests_no_difference
    {β : Type v} (a b : β) :
    ¬ TestDifferent (fun e : Empty => nomatch e) a b := by
  intro h
  apply h
  intro e
  exact nomatch e

end MathGraph.Calculus
