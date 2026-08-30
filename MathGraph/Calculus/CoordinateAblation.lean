import MathGraph.Calculus.DirectedTransportGrounding

universe u v w

namespace MathGraph.Calculus

/-- Erase the test coordinate by pooling every witness into one anonymous
witness type. This keeps witnesses but forgets which distinction produced them. -/
def ErasedWitness {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) : Type (max w v) :=
  Sigma (fun k => W k x)

/-- Transport after coordinate erasure may send a witness from one test to a
witness from a completely different test. -/
def ErasedTransport {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x y : α) : Type (max w v) :=
  ErasedWitness W x → ErasedWitness W y

/-- Coordinate-preserving directed transport always induces anonymous
transport after erasure. -/
def directed_to_erased
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    DirectedTransport W x y → ErasedTransport W x y :=
  fun h p => ⟨p.1, h p.1 p.2⟩

/-- Small finite witness world: each state has exactly one witness, but at a
different test coordinate. -/
def crossedCoordinateWitness : Bool → Bool → Type :=
  fun k x => match k, x with
    | false, false => Unit
    | true, true => Unit
    | false, true => Empty
    | true, false => Empty

/-- After erasing coordinates, the witness at `false` can be relabelled as the
witness at `true`. -/
def erased_false_to_true :
    ErasedTransport crossedCoordinateWitness false true := by
  intro p
  rcases p with ⟨k, hk⟩
  cases k with
  | false => exact ⟨true, ()⟩
  | true => exact nomatch hk

/-- And conversely: anonymous mutual reachability exists. -/
def erased_true_to_false :
    ErasedTransport crossedCoordinateWitness true false := by
  intro p
  rcases p with ⟨k, hk⟩
  cases k with
  | false => exact nomatch hk
  | true => exact ⟨false, ()⟩

/-- But coordinate-preserving transport from `false` to `true` is impossible:
the `false` coordinate would require `Unit → Empty`. -/
def indexed_false_not_reach_true :
    DirectedTransport crossedCoordinateWitness false true → Empty := by
  intro h
  exact h false ()

/-- The reverse indexed direction is independently impossible at the `true`
coordinate. -/
def indexed_true_not_reach_false :
    DirectedTransport crossedCoordinateWitness true false → Empty := by
  intro h
  exact h true ()

/-- Decisive ablation: forgetting which test a witness belongs to creates
spurious mutual transport that the indexed substrate correctly rejects. Thus
witness existence alone is insufficient; distinction coordinates carry causal
information needed by the transport calculus. -/
def coordinate_erasure_creates_spurious_identity :
    (ErasedTransport crossedCoordinateWitness false true) ×
    (ErasedTransport crossedCoordinateWitness true false) ×
    (DirectedTransport crossedCoordinateWitness false true → Empty) ×
    (DirectedTransport crossedCoordinateWitness true false → Empty) :=
  ⟨erased_false_to_true,
   erased_true_to_false,
   indexed_false_not_reach_true,
   indexed_true_not_reach_false⟩

end MathGraph.Calculus
