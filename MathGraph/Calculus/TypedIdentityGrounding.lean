import MathGraph.Calculus.DirectWitnessGrounding

universe u v w

namespace MathGraph.Calculus

/-- Identity itself as data, not as a proposition. An inhabitant gives a
bidirectional witness transport for every test. -/
def TypedIdentity {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Type (max w v) :=
  (k : κ) → (W k x → W k y) × (W k y → W k x)

/-- Reflexive typed identity. -/
def typedIdentityRefl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) :
    TypedIdentity W x x :=
  fun _ => ⟨id, id⟩

/-- Typed identity reverses by exchanging the two transports. -/
def typedIdentitySymm
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    TypedIdentity W x y → TypedIdentity W y x :=
  fun h k => ⟨(h k).2, (h k).1⟩

/-- Typed identities compose by ordinary function composition. -/
def typedIdentityTrans
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y z : α} :
    TypedIdentity W x y → TypedIdentity W y z → TypedIdentity W x z :=
  fun hxy hyz k =>
    ⟨fun hx => (hyz k).1 ((hxy k).1 hx),
     fun hz => (hxy k).2 ((hyz k).2 hz)⟩

/-- Add a new witness family without leaving the type-valued layer. -/
def typedIdentityExtend {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) :
    WitnessIncidence.{u,v,w} (Sum κ Unit) α :=
  witnessExtend W c

/-- Refinement is itself a map of identity witness types: every identity at the
extended language restricts to an identity at the old language. -/
def typedIdentity_extension_refines
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α} :
    TypedIdentity (typedIdentityExtend W c) x y → TypedIdentity W x y :=
  fun h k => h (Sum.inl k)

/-- The new test component can be projected directly from an extended typed
identity. -/
def typedIdentity_new_component
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α} :
    TypedIdentity (typedIdentityExtend W c) x y →
      ((c x → c y) × (c y → c x)) :=
  fun h => h (Sum.inr ())

/-- A genuinely impossible new bidirectional transport makes the extended
identity type empty. The obstruction is expressed with `Empty`, not negation. -/
def typedIdentity_new_test_obstructs
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α}
    (blocked : ((c x → c y) × (c y → c x)) → Empty) :
    TypedIdentity (typedIdentityExtend W c) x y → Empty :=
  fun h => blocked (typedIdentity_new_component W c h)

/-- With no tests there is a canonical typed identity between every pair. -/
def empty_typedIdentity_collapses_all
    {α : Type u} (x y : α) :
    TypedIdentity
      (((fun k : Empty => nomatch k) : Empty → α → Type v)) x y :=
  fun k => nomatch k

/-- Duplicating each witness preserves typed identity in the forward direction. -/
def typedIdentity_duplicate_forward
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) {x y : α} :
    TypedIdentity W x y → TypedIdentity (witnessDuplicate W) x y :=
  fun h k =>
    ⟨fun s => match s with
      | Sum.inl a => Sum.inl ((h k).1 a)
      | Sum.inr a => Sum.inr ((h k).1 a),
     fun s => match s with
      | Sum.inl b => Sum.inl ((h k).2 b)
      | Sum.inr b => Sum.inr ((h k).2 b)⟩

/-- Duplicating each witness also reflects typed identity. -/
def typedIdentity_duplicate_backward
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) {x y : α} :
    TypedIdentity (witnessDuplicate W) x y → TypedIdentity W x y :=
  fun h k =>
    ⟨fun a => match (h k).1 (Sum.inl a) with
      | Sum.inl b => b
      | Sum.inr b => b,
     fun b => match (h k).2 (Sum.inl b) with
      | Sum.inl a => a
      | Sum.inr a => a⟩

/-- Truncating a typed identity to proposition-level pointwise existence is
constructive. This is the first point where the richer identity data is
forgotten. -/
theorem typedIdentity_implies_directWitnessSame
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : TypedIdentity W x y) : DirectWitnessSame W x y := by
  intro k
  exact ⟨(h k).1, (h k).2, True.intro⟩

/-- The proposition-level identity reconstructs one global typed identity only
when classical choice is admitted. Pointwise existential transports do not
constructively provide the dependent family of chosen transports. -/
noncomputable def directWitnessSame_to_typedIdentity_classical
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectWitnessSame W x y) : TypedIdentity W x y := by
  classical
  intro k
  have hf : ∃ f : W k x → W k y, ∃ g : W k y → W k x, True := h k
  let f : W k x → W k y := Classical.choose hf
  have hg : ∃ g : W k y → W k x, True := Classical.choose_spec hf
  let g : W k y → W k x := Classical.choose hg
  exact ⟨f, g⟩

/-- Every typed identity reaches the existing consequence calculus after
ordinary propositional forgetting. -/
theorem typedIdentity_implies_consequentialEq
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : TypedIdentity W x y) :
    ConsequentialEq (incidenceLanguage (witnessReflect W)) x y := by
  exact (witness_identity_matches_calculus W x y).mpr
    (directWitnessSame_implies_witnessSame
      (typedIdentity_implies_directWitnessSame h))

end MathGraph.Calculus
