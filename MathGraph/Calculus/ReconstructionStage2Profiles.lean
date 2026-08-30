import MathGraph.Calculus.ReconstructionFromBedrock

universe u v

namespace MathGraph.Calculus

/-- Every endpoint in the raw directed world determines its incoming continuation
profile: for each possible source, the type of finite paths into the endpoint. -/
def IncomingPathProfile {Ω : Type u}
    (G : Ω → Ω → Type v) (x : Ω) : Ω → Type (max u v) :=
  fun k => FreePath G k x

/-- A path `x → y` acts on every incoming path by postcomposition, so raw
continuation generates profile transport without any additional observation
structure. -/
def path_to_incomingProfileTransport
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    FreePath G x y →
      ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) :=
  fun p k q => FreePath.append q p

/-- Conversely, any transport between the incoming profiles contains a path
`x → y`: apply it at source `x` to the zero-length path at `x`. -/
def incomingProfileTransport_to_path
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) →
      FreePath G x y :=
  fun h => h x .nil

/-- The generated transport map recovers its originating path exactly. -/
theorem path_profile_path_roundtrip
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (p : FreePath G x y) :
    incomingProfileTransport_to_path
      (path_to_incomingProfileTransport p) = p :=
  rfl

/-- Mutual finite continuation therefore generates mutual profile transport. -/
def generatedIdentity_to_profileMutual
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    GeneratedIdentity G x y →
      (ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) ×
       ProfileTransport (IncomingPathProfile G y) (IncomingPathProfile G x)) :=
  fun h =>
    ⟨path_to_incomingProfileTransport h.1,
     path_to_incomingProfileTransport h.2⟩

/-- And mutual profile transport is sufficient to recover mutual finite
continuation, constructively and without choice. -/
def profileMutual_to_generatedIdentity
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    (ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) ×
     ProfileTransport (IncomingPathProfile G y) (IncomingPathProfile G x)) →
      GeneratedIdentity G x y :=
  fun h =>
    ⟨incomingProfileTransport_to_path h.1,
     incomingProfileTransport_to_path h.2⟩

/-- Stage-2 reconstruction certificate: the witness-profile transport layer is
not a new primitive. It is generated canonically from bedrock paths, and its
mutual reachability is constructively sufficient to recover generated identity. -/
def reconstruction_stage2_certificate
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    (GeneratedIdentity G x y →
      (ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) ×
       ProfileTransport (IncomingPathProfile G y) (IncomingPathProfile G x))) ×
    ((ProfileTransport (IncomingPathProfile G x) (IncomingPathProfile G y) ×
      ProfileTransport (IncomingPathProfile G y) (IncomingPathProfile G x)) →
      GeneratedIdentity G x y) :=
  ⟨generatedIdentity_to_profileMutual,
   profileMutual_to_generatedIdentity⟩

end MathGraph.Calculus
