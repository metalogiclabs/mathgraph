import MathGraph.Calculus.WitnessIncidenceGrounding

universe u v w

namespace MathGraph.Calculus

/-- Direct witness-level identity. No `Nonempty`, `Prop`-valued incidence,
comparison relation, or outcome equality occurs in the definition: for every
test, witnesses can be transported in both directions. -/
def DirectWitnessSame {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Prop :=
  ∀ k, (W k x → W k y) × (W k y → W k x)

/-- Direct distinction is failure of bidirectional witness transport. -/
def DirectWitnessDifferent {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Prop :=
  ¬ DirectWitnessSame W x y

theorem directWitnessSame_refl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) :
    DirectWitnessSame W x x := by
  intro k
  exact ⟨id, id⟩

theorem directWitnessSame_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessSame W x y) : DirectWitnessSame W y x := by
  intro k
  exact ⟨(h k).2, (h k).1⟩

theorem directWitnessSame_trans
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y z : α}
    (hxy : DirectWitnessSame W x y)
    (hyz : DirectWitnessSame W y z) :
    DirectWitnessSame W x z := by
  intro k
  exact ⟨fun hx => (hyz k).1 ((hxy k).1 hx),
         fun hz => (hxy k).2 ((hyz k).2 hz)⟩

theorem directWitnessDifferent_irrefl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) :
    ¬ DirectWitnessDifferent W x x := by
  intro h
  exact h (directWitnessSame_refl W x)

theorem directWitnessDifferent_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessDifferent W x y) :
    DirectWitnessDifferent W y x := by
  intro hyx
  exact h (directWitnessSame_symm hyx)

/-- Direct witness identity is already strong enough to imply occupancy
identity. `Nonempty` appears only in this downstream reflection theorem, not in
the foundational definition. -/
theorem directWitnessSame_implies_witnessSame
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessSame W x y) : WitnessSame W x y := by
  intro k
  constructor
  · intro hx
    rcases hx with ⟨a⟩
    exact ⟨(h k).1 a⟩
  · intro hy
    rcases hy with ⟨b⟩
    exact ⟨(h k).2 b⟩

/-- Therefore every direct distinction that is visible as an occupancy
separator remains a distinction after logical reflection. -/
theorem witnessSeparated_implies_directWitnessDifferent
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : WitnessSeparated W x y) : DirectWitnessDifferent W x y := by
  intro hDirect
  exact (witnessSeparated_implies_different h)
    (directWitnessSame_implies_witnessSame hDirect)

/-- Add one raw witness family without any occupancy reflection. -/
def directWitnessExtend {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) :
    WitnessIncidence.{u,v,w} (Sum κ Unit) α :=
  witnessExtend W c

/-- Language extension refines direct witness identity constructively. -/
theorem directWitness_extension_refines
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α}
    (h : DirectWitnessSame (directWitnessExtend W c) x y) :
    DirectWitnessSame W x y := by
  intro k
  exact h (Sum.inl k)

/-- A new witness family whose witness types do not admit maps both ways
forces a strict direct-identity split. -/
theorem directWitness_new_test_forces_split
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α}
    (hOld : DirectWitnessSame W x y)
    (hNew : ¬ ((c x → c y) × (c y → c x))) :
    DirectWitnessSame W x y ∧
      ¬ DirectWitnessSame (directWitnessExtend W c) x y := by
  refine ⟨hOld, ?_⟩
  intro h
  exact hNew (h (Sum.inr ()))

/-- With no tests, all states are directly witness-indistinguishable. -/
theorem empty_directWitness_collapses_all
    {α : Type u} (x y : α) :
    DirectWitnessSame
      (((fun k : Empty => nomatch k) : Empty → α → Type v)) x y := by
  intro k
  exact nomatch k

/-- Direct witness identity is insensitive to duplicating every witness. -/
theorem duplicate_preserves_directWitnessSame
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) :
    DirectWitnessSame (witnessDuplicate W) x y ↔
      DirectWitnessSame W x y := by
  constructor
  · intro h k
    constructor
    · intro a
      have d : Sum (W k x) (W k x) := Sum.inl a
      cases (h k).1 d with
      | inl b => exact b
      | inr b => exact b
    · intro b
      have d : Sum (W k y) (W k y) := Sum.inl b
      cases (h k).2 d with
      | inl a => exact a
      | inr a => exact a
  · intro h k
    constructor
    · intro s
      cases s with
      | inl a => exact Sum.inl ((h k).1 a)
      | inr a => exact Sum.inr ((h k).1 a)
    · intro s
      cases s with
      | inl b => exact Sum.inl ((h k).2 b)
      | inr b => exact Sum.inr ((h k).2 b)

/-- Once classical choice is admitted, occupancy identity reconstructs direct
witness transport exactly. This theorem marks the logical boundary: the
`Nonempty` quotient loses witness-producing content constructively, although
it is extensionally complete classically. -/
theorem witnessSame_implies_directWitnessSame_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : WitnessSame W x y) : DirectWitnessSame W x y := by
  classical
  intro k
  constructor
  · intro a
    exact Classical.choice ((h k).mp ⟨a⟩)
  · intro b
    exact Classical.choice ((h k).mpr ⟨b⟩)

/-- Exact classical equivalence between the richer direct transport identity
and the previous occupancy identity. -/
theorem directWitnessSame_iff_witnessSame_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    DirectWitnessSame W x y ↔ WitnessSame W x y := by
  constructor
  · exact directWitnessSame_implies_witnessSame
  · exact witnessSame_implies_directWitnessSame_classical

/-- The direct layer therefore reaches the existing consequence calculus after
one explicit classical reflection step, while its identity/refinement core did
not require `Nonempty` at all. -/
theorem directWitness_identity_matches_calculus_classical
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) :
    ConsequentialEq (incidenceLanguage (witnessReflect W)) x y ↔
      DirectWitnessSame W x y := by
  classical
  exact (witness_identity_matches_calculus W x y).trans
    (directWitnessSame_iff_witnessSame_classical.symm)

end MathGraph.Calculus
