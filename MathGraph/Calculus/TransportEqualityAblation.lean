import MathGraph.Calculus.DirectedTransportGrounding

universe u v w

namespace MathGraph.Calculus

/-- A witness family that gives exactly one witness at every state. Distinct
states therefore have transports in both directions for every test. -/
def indiscreteWitness : Unit → Bool → Type :=
  fun _ _ => Unit

/-- `false` reaches `true` in the indiscrete witness family. -/
def indiscrete_false_reaches_true :
    DirectedTransport indiscreteWitness false true :=
  fun _ _ => ()

/-- `true` reaches `false` in the same witness family. -/
def indiscrete_true_reaches_false :
    DirectedTransport indiscreteWitness true false :=
  fun _ _ => ()

/-- Hence the two distinct states carry a full typed identity witness. -/
def indiscrete_false_typedIdentity_true :
    TypedIdentity indiscreteWitness false true :=
  mutualDirected_to_typedIdentity
    indiscrete_false_reaches_true
    indiscrete_true_reaches_false

/-- Nevertheless the underlying Bool constructors are not equal. -/
def bool_false_not_equal_true : false = true → Empty := by
  intro h
  cases h

/-- Finite countermodel: mutual directed transport, and therefore typed
identity, does not force equality of underlying states. Equality is additional
structure not derivable from the transport substrate alone. -/
def mutual_transport_does_not_force_state_equality :
    TypedIdentity indiscreteWitness false true ×
      (false = true → Empty) :=
  ⟨indiscrete_false_typedIdentity_true, bool_false_not_equal_true⟩

/-- The same separation can be stated directly at the one-way substrate: both
directions exist while state equality remains impossible. -/
def mutual_directed_does_not_force_state_equality :
    (DirectedTransport indiscreteWitness false true ×
      DirectedTransport indiscreteWitness true false) ×
      (false = true → Empty) :=
  ⟨⟨indiscrete_false_reaches_true, indiscrete_true_reaches_false⟩,
   bool_false_not_equal_true⟩

end MathGraph.Calculus
