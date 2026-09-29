import Theorems.Thm_IsLocalRing_isRegular_of_systemOfParameters
import CrystalAnthropicConsumer.Bridge

open IsLocalRing RingTheory

namespace CrystalAnthropicConsumer

/--
Reuse a real theorem from the Anthropic FLT corpus, but expose only the
consumer's protected consequence. The 140KB-scale source proof is not copied.
-/
theorem reused_systemOfParameters_as_weak
    {R : Type*} [CommRing R] [IsLocalRing R] [IsNoetherianRing R]
    (hCM : (Module.depth R R : WithBot ℕ∞) = ringKrullDim R)
    {d : ℕ} (hdim : ringKrullDim R = d)
    (xs : List R) (hlen : xs.length = d)
    (hmem : ∀ y ∈ xs, y ∈ maximalIdeal R)
    (hsop : ringKrullDim (R ⧸ Ideal.ofList xs) = 0) :
    WeakRegularityView xs := by
  apply regular_to_weak_view xs
  exact IsLocalRing.isRegular_of_systemOfParameters hCM hdim xs hlen hmem hsop

end CrystalAnthropicConsumer
