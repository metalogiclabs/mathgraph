import MathGraph.Calculus.StateCarrierAblation

universe u v w

namespace MathGraph.Calculus

/-- The representation-free residue of the transport calculus: objects, a
Type-valued directed hom, an identity witness at every object, and composition.
No test coordinates, witness profiles, Prop-valued relation, or equality laws
are assumed. -/
structure BareTransportAlgebra where
  Obj : Type u
  Hom : Obj → Obj → Type v
  ident : (x : Obj) → Hom x x
  comp : {x y z : Obj} → Hom x y → Hom y z → Hom x z

/-- Mutual reachability is the symmetric identity data induced by a directed
hom. It is data, not propositional equality. -/
def Mutual {Ω : Type u} (R : Ω → Ω → Type v) (x y : Ω) : Type v :=
  R x y × R y x

/-- Identity is derivable from the bare identity witness. -/
def bareMutualRefl (A : BareTransportAlgebra.{u,v}) (x : A.Obj) :
    Mutual A.Hom x x :=
  ⟨A.ident x, A.ident x⟩

/-- Symmetry of mutuality requires no primitive symmetry operation: swap the
witnesses. -/
def bareMutualSymm (A : BareTransportAlgebra.{u,v}) {x y : A.Obj} :
    Mutual A.Hom x y → Mutual A.Hom y x :=
  fun h => ⟨h.2, h.1⟩

/-- Transitivity is inherited solely from directed composition. -/
def bareMutualTrans (A : BareTransportAlgebra.{u,v}) {x y z : A.Obj} :
    Mutual A.Hom x y → Mutual A.Hom y z → Mutual A.Hom x z :=
  fun hxy hyz =>
    ⟨A.comp hxy.1 hyz.1, A.comp hyz.2 hxy.2⟩

/-- Every coordinate-indexed witness-profile presentation compiles into the
bare algebra. The coordinate type is hidden inside the implementation of Hom;
it is not part of the abstract interface. -/
def profileBareTransport (κ : Type w) : BareTransportAlgebra.{max (v+1) w, max w v} where
  Obj := WitnessProfile.{v,w} κ
  Hom := ProfileTransport
  ident := profileRefl
  comp := fun f g => profileComp f g

/-- The bare hom of the compiled profile algebra reduces definitionally to the
original pointwise transport. -/
theorem profileBare_hom_exact {κ : Type w}
    (P Q : WitnessProfile.{v,w} κ) :
    (profileBareTransport κ).Hom P Q = ProfileTransport P Q :=
  rfl

/-- Removing identity witnesses really loses reflexivity. This finite relation
has a directed arrow `false → true` but no self-arrow at `false`. -/
def noIdentityHom : Bool → Bool → Type :=
  fun x y => match x, y with
    | false, true => Unit
    | _, _ => Empty

/-- Without an identity primitive, even mutual reflexivity need not exist. -/
def no_identity_means_no_mutual_reflexivity :
    Mutual noIdentityHom false false → Empty :=
  fun h => h.1

/-- Three objects for the composition ablation. -/
inductive Three where
  | a | b | c

/-- Adjacent objects are mutually connected, but the endpoints are not. -/
def noCompositionHom : Three → Three → Type :=
  fun x y => match x, y with
    | Three.a, Three.a => Unit
    | Three.b, Three.b => Unit
    | Three.c, Three.c => Unit
    | Three.a, Three.b => Unit
    | Three.b, Three.a => Unit
    | Three.b, Three.c => Unit
    | Three.c, Three.b => Unit
    | _, _ => Empty

def noComp_mutual_ab : Mutual noCompositionHom Three.a Three.b :=
  ⟨(), ()⟩

def noComp_mutual_bc : Mutual noCompositionHom Three.b Three.c :=
  ⟨(), ()⟩

/-- Yet the endpoint mutuality is impossible. Thus transitivity of induced
identity cannot be recovered from reflexive directed data without some
composition principle. -/
def no_composition_means_no_mutual_transitivity :
    Mutual noCompositionHom Three.a Three.c → Empty :=
  fun h => h.1

/-- Decisive descent certificate: coordinates and witness profiles are not
needed by the abstract identity/composition core, while identity witnesses and
composition are independently necessary for its reflexive/transitive laws. -/
def bare_transport_descent_certificate :
    (Mutual noIdentityHom false false → Empty) ×
    Mutual noCompositionHom Three.a Three.b ×
    Mutual noCompositionHom Three.b Three.c ×
    (Mutual noCompositionHom Three.a Three.c → Empty) :=
  ⟨no_identity_means_no_mutual_reflexivity,
   noComp_mutual_ab,
   noComp_mutual_bc,
   no_composition_means_no_mutual_transitivity⟩

end MathGraph.Calculus
