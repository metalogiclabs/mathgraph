import MathGraph.Calculus.GeneralOrbitStabilizerBoundary
import MathGraph.Calculus.SymmetryBreakingAnchor

namespace MathGraph.Calculus

/-- A runtime contact channel for the symmetric two-point seed.

`R` is the response alphabet delivered by the environment. `flip` describes
how the same external contact is renamed under the nontrivial Bool symmetry,
and `decode` turns the received response into the operational representative.
Equivariance says that renaming the interaction response renames the decoded
representative rather than privileging a hidden internal coordinate. -/
structure BoolContactChannel (R : Type) where
  flip : R → R
  decode : R → Bool
  decode_flip : ∀ r : R, decode (flip r) = Bool.not (decode r)

namespace BoolContactChannel

/-- A symmetry-breaking response cannot itself be fixed by the response-side
symmetry.  Otherwise equivariance would force a Bool point to equal its own
negation. -/
theorem no_fixed_response {R : Type} (C : BoolContactChannel R) (r : R) :
    C.flip r ≠ r := by
  intro hFix
  have h := C.decode_flip r
  rw [hFix] at h
  cases hDec : C.decode r <;> simp [hDec] at h

/-- Consequently a completely symmetry-invariant one-point response alphabet
cannot transmit the missing orientation.  Interaction does not create
symmetry-breaking information ex nihilo. -/
theorem no_unit_contact_channel :
    ¬ Nonempty (BoolContactChannel Unit) := by
  intro h
  rcases h with ⟨C⟩
  exact C.no_fixed_response () (Subsingleton.elim _ _)

/-- The minimal positive control: one Bool response bit, transformed by Bool
negation, is an equivariant runtime contact channel. -/
def bitContact : BoolContactChannel Bool where
  flip := Bool.not
  decode := fun b => b
  decode_flip := by
    intro b
    rfl

/-- A received interaction response generates the ordered task only after
contact.  No distinguished Bool point is stored in the internal cold seed. -/
def taskFromResponse {R : Type} (C : BoolContactChannel R) (r : R) :
    Stage26TaskBoundary Bool :=
  Stage29TaskFromAnchor (C.decode r)

/-- The interaction-generated task is itself equivariant: flipping the external
response reverses the operational source/target order. -/
theorem taskFromResponse_flip {R : Type} (C : BoolContactChannel R) (r : R) :
    C.taskFromResponse (C.flip r) =
      (⟨(C.taskFromResponse r).target, (C.taskFromResponse r).source⟩ :
        Stage26TaskBoundary Bool) := by
  unfold taskFromResponse Stage29TaskFromAnchor
  rw [C.decode_flip r]
  cases h : C.decode r <;> rfl

/-- Turn one received response into the active verifier boundary.  The history
is initially empty; both task endpoints are generated from the contact reply. -/
def boundaryFromResponse {R : Type} (C : BoolContactChannel R) (r : R) :
    GeneratedVerifierBoundary Bool :=
  { history := []
    current := C.taskFromResponse r }

/-- Every valid runtime response selects a genuine residual-derived operational
direction in the cold substrate.  Which direction is selected is determined by
the encounter, not by an initialized distinguished endpoint. -/
theorem response_licenses_development {R : Type}
    (C : BoolContactChannel R) (r : R) :
    Nonempty
      (Stage20Generator Stage13G0
        (C.boundaryFromResponse r).probes
        (C.boundaryFromResponse r).current.source
        (C.boundaryFromResponse r).current.target) := by
  cases hDec : C.decode r
  · have hTask : C.taskFromResponse r = Stage28BoolTask := by
      unfold taskFromResponse
      rw [hDec]
      exact stage29_false_anchor_recovers_forward_task
    rw [show (C.boundaryFromResponse r).current = Stage28BoolTask by exact hTask]
    exact stage28_current_task_licenses_development
  · have hTask : C.taskFromResponse r =
        (⟨true, false⟩ : Stage26TaskBoundary Bool) := by
      unfold taskFromResponse
      rw [hDec]
      exact stage29_true_anchor_recovers_reverse_task
    rw [show (C.boundaryFromResponse r).current =
      (⟨true, false⟩ : Stage26TaskBoundary Bool) by exact hTask]
    refine ⟨⟨true, ?_⟩⟩
    constructor
    · exact stage21_cold_true_generic_residual
    · exact ⟨(.nil : FreePath Stage13G0 true true)⟩

/-- Retaining the encountered task generates the next selective observational
state from the transcript.  The stored coordinate is exactly the representative
decoded from the interaction response. -/
theorem learning_response_generates_selective_state {R : Type}
    (C : BoolContactChannel R) (r : R) :
    (GeneratedVerifierBoundary.learn (C.boundaryFromResponse r)).history.sources =
      ([C.decode r] : GeneratedInterface Bool) := by
  rfl

end BoolContactChannel

/-- Decisive self-hosting-boundary certificate.

A symmetry-breaking representative need not be preloaded into the machine: a
runtime external encounter can supply a response, from which the ordered task,
residual-derived direction, and next selective observation coordinate are all
generated.  But the external information has not disappeared.  Equivariance
forces every valid response to move under the seed symmetry, and the one-point
(symmetry-invariant) response alphabet is impossible.  Thus the irreducible
boundary can be moved from initialization into interaction, but cannot be
removed: it is symmetry-breaking information carried by environmental contact. -/
theorem interaction_generated_boundary_certificate :
    (¬ Nonempty (BoolContactChannel Unit)) ∧
    (∀ r : Bool,
      BoolContactChannel.bitContact.taskFromResponse
          (BoolContactChannel.bitContact.flip r) =
        (⟨(BoolContactChannel.bitContact.taskFromResponse r).target,
          (BoolContactChannel.bitContact.taskFromResponse r).source⟩ :
          Stage26TaskBoundary Bool)) ∧
    (∀ r : Bool,
      Nonempty
        (Stage20Generator Stage13G0
          (BoolContactChannel.bitContact.boundaryFromResponse r).probes
          (BoolContactChannel.bitContact.boundaryFromResponse r).current.source
          (BoolContactChannel.bitContact.boundaryFromResponse r).current.target)) ∧
    (∀ r : Bool,
      (GeneratedVerifierBoundary.learn
        (BoolContactChannel.bitContact.boundaryFromResponse r)).history.sources =
        ([r] : GeneratedInterface Bool)) := by
  refine ⟨BoolContactChannel.no_unit_contact_channel, ?_, ?_, ?_⟩
  · intro r
    exact BoolContactChannel.bitContact.taskFromResponse_flip r
  · intro r
    exact BoolContactChannel.bitContact.response_licenses_development r
  · intro r
    exact BoolContactChannel.bitContact.learning_response_generates_selective_state r

end MathGraph.Calculus
