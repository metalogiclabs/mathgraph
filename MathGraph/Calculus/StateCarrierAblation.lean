import MathGraph.Calculus.CoordinateAblation

universe u v w

namespace MathGraph.Calculus

/-- Remove the explicit state carrier. A state is represented only by its
profile of witness types across distinction coordinates. -/
def WitnessProfile (κ : Type w) := κ → Type v

/-- The foundational arrow on profiles is pointwise witness transport. -/
def ProfileTransport {κ : Type w}
    (P Q : WitnessProfile.{v,w} κ) : Type (max w v) :=
  (k : κ) → P k → Q k

/-- Profile transport has identity arrows without any state equality. -/
def profileRefl {κ : Type w}
    (P : WitnessProfile.{v,w} κ) : ProfileTransport P P :=
  fun _ => id

/-- Profile transport composes pointwise. -/
def profileComp {κ : Type w}
    {P Q R : WitnessProfile.{v,w} κ} :
    ProfileTransport P Q → ProfileTransport Q R → ProfileTransport P R :=
  fun f g k x => g k (f k x)

/-- Every state in a witness-incidence presentation determines a profile. -/
def stateProfile {κ : Type w} {α : Type u}
    (W : WitnessIncidence.{u,v,w} κ α) (x : α) : WitnessProfile.{v,w} κ :=
  fun k => W k x

/-- Directed transport in the old state-carrier presentation is exactly profile
transport between the corresponding profiles. No theorem or choice principle is
needed: the two types are definitionally the same data. -/
def directed_to_profile
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    DirectedTransport W x y →
      ProfileTransport (stateProfile W x) (stateProfile W y) :=
  fun h => h

/-- Conversely every profile transport is already a directed transport between
the represented states. -/
def profile_to_directed
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α} :
    ProfileTransport (stateProfile W x) (stateProfile W y) →
      DirectedTransport W x y :=
  fun h => h

/-- The round trips reduce to the original transport functions. -/
theorem directed_profile_roundtrip
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : DirectedTransport W x y) :
    profile_to_directed (directed_to_profile h) = h :=
  rfl

theorem profile_directed_roundtrip
    {κ : Type w} {α : Type u}
    {W : WitnessIncidence.{u,v,w} κ α} {x y : α}
    (h : ProfileTransport (stateProfile W x) (stateProfile W y)) :
    directed_to_profile (profile_to_directed h) = h :=
  rfl

/-- Two distinct carrier states may present exactly the same witness profile.
The carrier labels therefore contain information that is invisible to the
foundational transport calculus. -/
def duplicateCarrierWitness : Unit → Bool → Type :=
  fun _ _ => Unit

/-- Distinct Bool states have mutual profile transport because their profiles
are identical, despite the carrier states themselves being unequal. -/
def duplicateCarrier_mutual_profile_transport :
    ProfileTransport
        (stateProfile duplicateCarrierWitness false)
        (stateProfile duplicateCarrierWitness true) ×
    ProfileTransport
        (stateProfile duplicateCarrierWitness true)
        (stateProfile duplicateCarrierWitness false) :=
  ⟨fun _ => id, fun _ => id⟩

/-- Yet the carrier labels remain genuinely different. -/
def duplicateCarrier_states_not_equal : false = true → Empty := by
  intro h
  cases h

/-- Decisive state-carrier ablation: every old transport is exactly transport
between profiles, while distinct carrier labels can be observationally inert.
Thus `α` is presentation structure, not required by the transport core. -/
def state_carrier_is_extrinsic_to_transport_core :
    (ProfileTransport
        (stateProfile duplicateCarrierWitness false)
        (stateProfile duplicateCarrierWitness true)) ×
    (ProfileTransport
        (stateProfile duplicateCarrierWitness true)
        (stateProfile duplicateCarrierWitness false)) ×
    (false = true → Empty) :=
  ⟨duplicateCarrier_mutual_profile_transport.1,
   duplicateCarrier_mutual_profile_transport.2,
   duplicateCarrier_states_not_equal⟩

end MathGraph.Calculus
