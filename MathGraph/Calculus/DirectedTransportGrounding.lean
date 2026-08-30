import MathGraph.Calculus.TypedIdentityGrounding

universe u v w

namespace MathGraph.Calculus

/-- The one-way substrate: for every test, transport witnesses from `x` to `y`.
No reverse map, equality, proposition-valued identity, or symmetry is assumed. -/
def DirectedTransport {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Type (max w v) :=
  (k : κ) → W k x → W k y

/-- Directed transport is reflexive by identity maps. -/
def directedRefl
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) :
    DirectedTransport W x x :=
  fun _ => id

/-- Directed transport composes without any symmetry assumption. -/
def directedComp
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y z : α} :
    DirectedTransport W x y → DirectedTransport W y z →
      DirectedTransport W x z :=
  fun f g k a => g k (f k a)

/-- Adding a test refines directed reachability: an extended transport restricts
canonically to the old test family. -/
def directed_extension_refines
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α} :
    DirectedTransport (witnessExtend W c) x y → DirectedTransport W x y :=
  fun h k => h (Sum.inl k)

/-- Project the newly added directed component. -/
def directed_new_component
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α} :
    DirectedTransport (witnessExtend W c) x y → (c x → c y) :=
  fun h => h (Sum.inr ())

/-- A blocked new one-way map destroys reachability in that direction. -/
def directed_new_test_obstructs
    {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (c : α → Type v) {x y : α}
    (blocked : (c x → c y) → Empty) :
    DirectedTransport (witnessExtend W c) x y → Empty :=
  fun h => blocked (directed_new_component W c h)

/-- With no tests, every state reaches every other state. -/
def empty_directed_collapses_all
    {α : Type u} (x y : α) :
    DirectedTransport
      (((fun k : Empty => nomatch k) : Empty → α → Type v)) x y :=
  fun k => nomatch k

/-- Mutual directed reachability constructs the previous typed identity exactly,
with no classical logic or propositional truncation. -/
def mutualDirected_to_typedIdentity
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    DirectedTransport W x y → DirectedTransport W y x → TypedIdentity W x y :=
  fun f g k => ⟨f k, g k⟩

/-- A typed identity forgets to each directed component constructively. -/
def typedIdentity_to_directed_forward
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    TypedIdentity W x y → DirectedTransport W x y :=
  fun h k => (h k).1

def typedIdentity_to_directed_backward
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    TypedIdentity W x y → DirectedTransport W y x :=
  fun h k => (h k).2

/-- Hence typed identity is not primitive symmetry: it is the conjunction, at
the data level, of two independently directed transport capabilities. -/
def typedIdentity_from_mutualDirected
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    (DirectedTransport W x y × DirectedTransport W y x) → TypedIdentity W x y :=
  fun h => mutualDirected_to_typedIdentity h.1 h.2

/-- Concrete asymmetric witness family: `false` has no witness and `true` has
one witness. Transport from `false` to `true` exists vacuously. -/
def asymmetricWitness : Unit → Bool → Type :=
  fun _ b => if b then Unit else Empty

def false_reaches_true :
    DirectedTransport asymmetricWitness false true := by
  intro k h
  cases k
  simp [asymmetricWitness] at h

/-- But the reverse transport is impossible. This finite countermodel proves
symmetry is not derivable from directed transport + reflexivity + composition. -/
def true_not_reach_false :
    DirectedTransport asymmetricWitness true false → Empty := by
  intro h
  have f := h ()
  have u : asymmetricWitness () true := by
    simp [asymmetricWitness]
  have e : asymmetricWitness () false := f u
  simpa [asymmetricWitness] using e

/-- Therefore mutual reachability is strictly stronger than one-way reachability
in the same raw witness substrate. -/
def one_way_does_not_force_mutual :
    DirectedTransport asymmetricWitness false true ×
      (DirectedTransport asymmetricWitness true false → Empty) :=
  ⟨false_reaches_true, true_not_reach_false⟩

end MathGraph.Calculus
