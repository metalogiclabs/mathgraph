import MathGraph.Calculus.ReconstructionStage3Logic
import MathGraph.Calculus.Separation

universe u v

namespace MathGraph.Calculus

/-- Separation reconstructed directly from the bedrock-generated reachability
language: two endpoints are apart when some source can reach exactly one of
them at the reflected Prop level. -/
def BedrockSeparated {Ω : Type u}
    (G : Ω → Ω → Type v) (x y : Ω) : Prop :=
  Separated (IncomingReachabilityLanguage G) x y

/-- Concrete generated identity rules out reconstructed separation. -/
theorem generatedIdentity_not_bedrockSeparated
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : GeneratedIdentity G x y) :
    ¬ BedrockSeparated G x y :=
  (consequentialEq_iff_not_separated
    (IncomingReachabilityLanguage G) x y).mp
      (generatedIdentity_to_consequentialEq h)

/-- At the Prop-reflected layer, non-separation recovers existence of generated
identity. Concrete path witnesses remain truncated. -/
theorem not_bedrockSeparated_to_nonempty_generatedIdentity
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : ¬ BedrockSeparated G x y) :
    Nonempty (GeneratedIdentity G x y) :=
  consequentialEq_to_nonempty_generatedIdentity
    ((consequentialEq_iff_not_separated
      (IncomingReachabilityLanguage G) x y).mpr h)

/-- Exact Prop-level bridge produced by the reconstruction: existence of mutual
finite continuation is equivalent to non-separation in the generated logical
language. -/
theorem nonempty_generatedIdentity_iff_not_bedrockSeparated
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    Nonempty (GeneratedIdentity G x y) ↔ ¬ BedrockSeparated G x y := by
  constructor
  · intro h
    rcases h with ⟨gid⟩
    exact generatedIdentity_not_bedrockSeparated gid
  · exact not_bedrockSeparated_to_nonempty_generatedIdentity

/-- The generated separation is irreflexive. -/
theorem bedrockSeparated_irrefl
    {Ω : Type u} (G : Ω → Ω → Type v) (x : Ω) :
    ¬ BedrockSeparated G x x :=
  separated_irrefl (IncomingReachabilityLanguage G) x

/-- The generated separation is symmetric. -/
theorem bedrockSeparated_symm
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω}
    (h : BedrockSeparated G x y) : BedrockSeparated G y x :=
  separated_symm h

/-- The generated separation is cotransitive. No apartness law is assumed at
bedrock; it appears after path closure and logical reflection. -/
theorem bedrockSeparated_cotrans
    {Ω : Type u} {G : Ω → Ω → Type v} {x y z : Ω}
    (h : BedrockSeparated G x z) :
    BedrockSeparated G x y ∨ BedrockSeparated G y z :=
  separated_cotrans h

/-- Stage-4 certificate: the lawful separation/apartness interface is recovered
above the Prop reflection, and its complement is exactly truncated generated
identity. -/
theorem reconstruction_stage4_certificate
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} :
    Nonempty (GeneratedIdentity G x y) ↔ ¬ BedrockSeparated G x y :=
  nonempty_generatedIdentity_iff_not_bedrockSeparated

end MathGraph.Calculus
