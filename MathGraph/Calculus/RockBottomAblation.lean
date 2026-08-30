import MathGraph.Calculus.RawTransportGenesis

universe u v

namespace MathGraph.Calculus

/-- A concrete continuation witness packages two endpoints and a finite path
between them. -/
def SomeContinuation {Ω : Type u} (G : Ω → Ω → Type v) :=
  Sigma (fun x => Sigma (fun y => FreePath G x y))

/-- If the object/end-point carrier is empty, there is no continuation witness
at all—not even a zero-length one. -/
def emptyObjectGenerator : Empty → Empty → Type :=
  fun x => nomatch x

def no_objects_no_continuation :
    SomeContinuation emptyObjectGenerator → Empty :=
  fun s => nomatch s.1

/-- A single object is enough for persistence-like self-continuation. -/
def unitEmptyGenerator : Unit → Unit → Type :=
  fun _ _ => Empty

def unit_zero_length_continuation :
    FreePath unitEmptyGenerator () () :=
  .nil

/-- A single object can even carry a primitive event. Distinct carrier states
are therefore not required merely for nontrivial path structure. -/
def unitLoopGenerator : Unit → Unit → Type :=
  fun _ _ => Unit

def unit_loop_continuation :
    FreePath unitLoopGenerator () () :=
  FreePath.ofGenerator ()

/-- The primitive loop is genuinely different from the zero-length path. -/
def unit_loop_not_nil :
    unit_loop_continuation = (.nil : FreePath unitLoopGenerator () ()) → Empty := by
  intro h
  cases h

/-- But if primitive generators are removed from a world with distinct
endpoints, free closure cannot manufacture a cross-endpoint transition. -/
def no_generators_no_cross_transition :
    FreePath (emptyGenerator (Ω := Bool)) false true → Empty :=
  emptyGenerator_no_false_to_true

/-- Conversely one raw generator is sufficient to create that transition. -/
def one_generator_creates_cross_transition :
    FreePath oneEdgeGenerator false true :=
  oneEdge_false_to_true

/-- Bedrock certificate for this calculus reconstruction. Endpoints are needed
for there to be any continuation witness at all; primitive directed generators
are needed for nontrivial cross-endpoint change. No identity, composition,
symmetry, equality, coordinates, or laws are primitive at this layer. -/
def rock_bottom_certificate :
    (SomeContinuation emptyObjectGenerator → Empty) ×
    FreePath unitEmptyGenerator () () ×
    (unit_loop_continuation = (.nil : FreePath unitLoopGenerator () ()) → Empty) ×
    (FreePath (emptyGenerator (Ω := Bool)) false true → Empty) ×
    FreePath oneEdgeGenerator false true :=
  ⟨no_objects_no_continuation,
   unit_zero_length_continuation,
   unit_loop_not_nil,
   no_generators_no_cross_transition,
   one_generator_creates_cross_transition⟩

end MathGraph.Calculus
