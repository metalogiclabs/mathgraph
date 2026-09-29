import Mathlib.RingTheory.Regular.RegularSequence

namespace CrystalAnthropicConsumer

/-- Crystal consequence-specific view: this consumer needs only weak regularity. -/
def WeakRegularityView {R : Type*} [CommRing R] (xs : List R) : Prop :=
  RingTheory.Sequence.IsWeaklyRegular R xs

/-- Verified projection from the stronger source theorem interface. -/
theorem regular_to_weak_view {R : Type*} [CommRing R] (xs : List R)
    (h : RingTheory.Sequence.IsRegular R xs) :
    WeakRegularityView xs :=
  h.toIsWeaklyRegular

end CrystalAnthropicConsumer
