import Theorems.Thm_fermat_last_theorem
import CrystalAnthropicConsumer.Bridge

namespace CrystalAnthropicConsumer

theorem imported_anthropic_as_positive :
    ∀ n : ℕ, 3 ≤ n → PositiveFLTFor n := by
  intro n hn a b c ha hb hc
  exact fermat_last_theorem n hn a b c ha hb hc

theorem reused_anthropic_as_mathlib : FermatLastTheorem := by
  intro n hn
  exact (positiveFLTFor_iff_mathlib n).mp (imported_anthropic_as_positive n hn)

end CrystalAnthropicConsumer
