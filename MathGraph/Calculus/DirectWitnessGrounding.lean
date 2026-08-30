import MathGraph.Calculus.WitnessIncidenceGrounding

universe u v w

namespace MathGraph.Calculus

/-- Direct witness-level identity. No `Nonempty`, `Prop`-valued incidence,
comparison relation, or outcome equality occurs in the definition. For every
test there merely exist witness transports in both directions. -/
def DirectWitnessSame {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Prop :=
  ∀ k, ∃ f : W k x → W k y, ∃ g : W k y → W k x, True

/-- Direct distinction is failure of bidirectional witness transport. -/
def DirectWitnessDifferent {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Prop :=
  ¬ DirectWitnessSame W x y

theorem directWitnessSame_refl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) :
    DirectWitnessSame W x x := by
  intro k
  exact ⟨id, id, True.intro⟩

theorem directWitnessSame_symm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessSame W x y) : DirectWitnessSame W y x := by
  intro k
  rcases h k with ⟨f, g, _⟩
  exact ⟨g, f, True.intro⟩

theorem directWitnessSame_trans
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y z : α}
    (hxy : DirectWitnessSame W x y)
    (hyz : DirectWitnessSame W y z) :
    DirectWitnessSame W x z := by
  intro k
  rcases hxy k with ⟨fxy, fyx, _⟩
  rcases hyz k with ⟨fyz, fzy, _⟩
  exact ⟨fun a => fyz (fxy a), fun c => fyx (fzy c), True.intro⟩

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

/-- Direct witness identity implies occupancy identity. `Nonempty` appears only
in this downstream reflection theorem, not in the foundational definition. -/
theorem directWitnessSame_implies_witnessSame
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessSame W x y) : WitnessSame W x y := by
  intro k
  rcases h k with ⟨f, g, _⟩
  constructor
  · intro hx
    rcases hx with ⟨a⟩
    exact ⟨f a⟩
  · intro hy
    rcases hy with ⟨b⟩
    exact ⟨g b⟩

/-- Every occupancy separator is also a direct witness distinction. -/
theorem witnessSeparated_implies_directWitnessDifferent
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : WitnessSeparated W x y) : DirectWitnessDifferent W x y := by
  intro hDirect
  exact (witnessSeparated_implies_different h)
    (directWitnessSame_implies_witnessSame hDirect)

/-- Add one raw witness family without occupancy reflection. -/
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

/-- Proposition saying maps exist both ways, without using `Nonempty`. -/
def BidirectionalMaps (A B : Type v) : Prop :=
  ∃ f : A → B, ∃ g : B → A, True

/-- A new witness family lacking bidirectional maps forces a strict split. -/
theorem directWitness_new_test_forces_split
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α}
    (hOld : DirectWitnessSame W x y)
    (hNew : ¬ BidirectionalMaps (c x) (c y)) :
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
    rcases h k with ⟨f, g, _⟩
    let projectY : Sum (W k y) (W k y) → W k y := fun s =>
      match s with
      | Sum.inl b => b
      | Sum.inr b => b
    let projectX : Sum (W k x) (W k x) → W k x := fun s =>
      match s with
      | Sum.inl a => a
      | Sum.inr a => a
    exact ⟨fun a => projectY (f (Sum.inl a)),
           fun b => projectX (g (Sum.inl b)), True.intro⟩
  · intro h k
    rcases h k with ⟨f, g, _⟩
    exact ⟨fun s => match s with
                    | Sum.inl a => Sum.inl (f a)
                    | Sum.inr a => Sum.inr (f a),
           fun s => match s with
                    | Sum.inl b => Sum.inl (g b)
                    | Sum.inr b => Sum.inr (g b), True.intro⟩

/-- Classical choice reconstructs direct transports from occupancy identity.
This marks the logical boundary: occupancy forgets witness-producing content
constructively, although it is extensionally complete classically. -/
theorem witnessSame_implies_directWitnessSame_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : WitnessSame W x y) : DirectWitnessSame W x y := by
  classical
  intro k
  let f : W k x → W k y := fun a => Classical.choice ((h k).mp ⟨a⟩)
  let g : W k y → W k x := fun b => Classical.choice ((h k).mpr ⟨b⟩)
  exact ⟨f, g, True.intro⟩

/-- Exact classical equivalence between direct transport identity and occupancy
identity. -/
theorem directWitnessSame_iff_witnessSame_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    DirectWitnessSame W x y ↔ WitnessSame W x y := by
  constructor
  · exact directWitnessSame_implies_witnessSame
  · exact witnessSame_implies_directWitnessSame_classical

/-- The direct layer reaches the existing consequence calculus only after the
explicit classical reflection step above. -/
theorem directWitness_identity_matches_calculus_classical
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) :
    ConsequentialEq (incidenceLanguage (witnessReflect W)) x y ↔
      DirectWitnessSame W x y := by
  classical
  exact (witness_identity_matches_calculus W x y).trans
    directWitnessSame_iff_witnessSame_classical.symm

end MathGraph.Calculus
