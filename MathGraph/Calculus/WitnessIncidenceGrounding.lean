import MathGraph.Calculus.IncidenceGrounding

universe u v w

namespace MathGraph.Calculus

/-- Bare witness-carrying incidence data. An incidence is a type of witnesses,
not a `Prop`-valued characteristic relation. No equality, comparison,
apartness, or truth-valued observation is stored in the data. -/
abbrev WitnessIncidence (κ : Type w) (α : Type u) := κ → α → Type v

/-- Logical incidence is obtained only by forgetting witness identity and
multiplicity and asking whether a witness exists. -/
def witnessReflect {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) : Incidence κ α :=
  fun k x => Nonempty (W k x)

/-- Static identity at the witness level depends only on occupancy of each
witness type. -/
def WitnessSame {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) : Prop :=
  ∀ k, Nonempty (W k x) ↔ Nonempty (W k y)

/-- Negative distinction is failure of witness-occupancy agreement. -/
def WitnessDifferent {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) : Prop :=
  ¬ WitnessSame W x y

/-- Positive, witness-producing separation records a concrete test whose
occupancy differs in a known direction. -/
def WitnessSeparated {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) : Prop :=
  ∃ k,
    (Nonempty (W k x) ∧ ¬ Nonempty (W k y)) ∨
    (¬ Nonempty (W k x) ∧ Nonempty (W k y))

theorem witnessSame_refl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x : α) :
    WitnessSame W x x := by
  intro k
  exact Iff.rfl

theorem witnessSame_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x y : α}
    (h : WitnessSame W x y) : WitnessSame W y x := by
  intro k
  exact (h k).symm

theorem witnessSame_trans
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x y z : α}
    (hxy : WitnessSame W x y) (hyz : WitnessSame W y z) :
    WitnessSame W x z := by
  intro k
  exact (hxy k).trans (hyz k)

theorem witnessDifferent_irrefl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x : α) :
    ¬ WitnessDifferent W x x := by
  intro h
  exact h (witnessSame_refl W x)

theorem witnessDifferent_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x y : α}
    (h : WitnessDifferent W x y) : WitnessDifferent W y x := by
  intro hyx
  exact h (witnessSame_symm hyx)

/-- Positive separation implies negative difference without excluded middle. -/
theorem witnessSeparated_implies_different
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x y : α}
    (h : WitnessSeparated W x y) : WitnessDifferent W x y := by
  intro hSame
  rcases h with ⟨k, hxy | hyx⟩
  · exact hxy.2 ((hSame k).mp hxy.1)
  · exact hyx.1 ((hSame k).mpr hyx.2)

theorem witnessSeparated_irrefl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x : α) :
    ¬ WitnessSeparated W x x := by
  intro h
  exact (witnessDifferent_irrefl W x) (witnessSeparated_implies_different h)

theorem witnessSeparated_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x y : α}
    (h : WitnessSeparated W x y) : WitnessSeparated W y x := by
  rcases h with ⟨k, hxy | hyx⟩
  · exact ⟨k, Or.inr ⟨hxy.2, hxy.1⟩⟩
  · exact ⟨k, Or.inl ⟨hyx.2, hyx.1⟩⟩

/-- Cotransitivity of positive separation needs only decidability of occupancy
for the one intermediate incidence being inspected; no global classical
choice is used. -/
theorem witnessSeparated_cotrans_of_decidable
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α}
    (dec : ∀ k x, Decidable (Nonempty (W k x)))
    {x z : α} (hxz : WitnessSeparated W x z) (y : α) :
    WitnessSeparated W x y ∨ WitnessSeparated W y z := by
  rcases hxz with ⟨k, hxz | hzx⟩
  · cases dec k y with
    | isTrue hy =>
        exact Or.inr ⟨k, Or.inl ⟨hy, hxz.2⟩⟩
    | isFalse hy =>
        exact Or.inl ⟨k, Or.inl ⟨hxz.1, hy⟩⟩
  · cases dec k y with
    | isTrue hy =>
        exact Or.inl ⟨k, Or.inr ⟨hzx.1, hy⟩⟩
    | isFalse hy =>
        exact Or.inr ⟨k, Or.inr ⟨hy, hzx.2⟩⟩

/-- The negative formulation obtains cotransitivity only after explicitly
crossing the classical logical boundary. -/
theorem witnessDifferent_cotrans_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{w,u,v} κ α} {x z : α}
    (hxz : WitnessDifferent W x z) (y : α) :
    WitnessDifferent W x y ∨ WitnessDifferent W y z := by
  classical
  change IncidenceDifferent (witnessReflect W) x z at hxz
  change IncidenceDifferent (witnessReflect W) x y ∨
    IncidenceDifferent (witnessReflect W) y z
  exact incidenceDifferent_cotrans hxz y

/-- Add one new witness family as a new test. -/
def witnessExtend {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (c : α → Type v) :
    WitnessIncidence.{w,u,v} (Sum κ Unit) α
  | Sum.inl k, x => W k x
  | Sum.inr _, x => c x

/-- Extension refines witness identity constructively. -/
theorem witness_extension_refines
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (c : α → Type v) {x y : α}
    (h : WitnessSame (witnessExtend W c) x y) :
    WitnessSame W x y := by
  intro k
  exact h (Sum.inl k)

/-- A new witness family with different occupancy forces an identity split. -/
theorem witness_new_test_forces_split
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (c : α → Type v) {x y : α}
    (hOld : WitnessSame W x y)
    (hNew : ¬ (Nonempty (c x) ↔ Nonempty (c y))) :
    WitnessSame W x y ∧ ¬ WitnessSame (witnessExtend W c) x y := by
  refine ⟨hOld, ?_⟩
  intro h
  exact hNew (h (Sum.inr ()))

/-- With no tests, every pair of states has the same empty witness profile. -/
theorem empty_witness_incidence_collapses_all
    {α : Type u} (x y : α) :
    WitnessSame (v := v) (fun k : Empty => nomatch k) x y := by
  intro k
  exact nomatch k

/-- Duplicate every witness. This changes raw witness multiplicity but not
whether an incidence is occupied. -/
def witnessDuplicate {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) : WitnessIncidence.{w,u,v} κ α :=
  fun k x => Sum (W k x) (W k x)

theorem duplicate_occupancy_iff
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (k : κ) (x : α) :
    Nonempty (witnessDuplicate W k x) ↔ Nonempty (W k x) := by
  constructor
  · intro h
    rcases h with ⟨s⟩
    cases s with
    | inl a => exact ⟨a⟩
    | inr a => exact ⟨a⟩
  · intro h
    rcases h with ⟨a⟩
    exact ⟨Sum.inl a⟩

/-- Static identity erases witness multiplicity: doubling all witnesses leaves
all state identifications unchanged. -/
theorem duplicate_preserves_witnessSame
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) :
    WitnessSame (witnessDuplicate W) x y ↔ WitnessSame W x y := by
  constructor
  · intro h k
    constructor
    · intro hx
      have hdx : Nonempty (witnessDuplicate W k x) :=
        (duplicate_occupancy_iff W k x).mpr hx
      have hdy := (h k).mp hdx
      exact (duplicate_occupancy_iff W k y).mp hdy
    · intro hy
      have hdy : Nonempty (witnessDuplicate W k y) :=
        (duplicate_occupancy_iff W k y).mpr hy
      have hdx := (h k).mpr hdy
      exact (duplicate_occupancy_iff W k x).mp hdx
  · intro h k
    constructor
    · intro hdx
      have hx := (duplicate_occupancy_iff W k x).mp hdx
      have hy := (h k).mp hx
      exact (duplicate_occupancy_iff W k y).mpr hy
    · intro hdy
      have hy := (duplicate_occupancy_iff W k y).mp hdy
      have hx := (h k).mpr hy
      exact (duplicate_occupancy_iff W k x).mpr hx

/-- Reflection to the previous incidence layer is exact for static identity. -/
theorem witnessSame_matches_reflection
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) :
    IncidenceSame (witnessReflect W) x y ↔ WitnessSame W x y := by
  exact Iff.rfl

/-- After occupancy reflection, the already verified consequence calculus is
recovered exactly. -/
theorem witness_identity_matches_calculus
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{w,u,v} κ α) (x y : α) :
    ConsequentialEq (incidenceLanguage (witnessReflect W)) x y ↔
      WitnessSame W x y := by
  exact (incidence_identity_matches_calculus (witnessReflect W) x y).trans
    (witnessSame_matches_reflection W x y)

end MathGraph.Calculus
