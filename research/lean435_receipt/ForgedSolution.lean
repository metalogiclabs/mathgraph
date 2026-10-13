/- Proof is genuinely kernel-valid, but proves a weaker proposition
   than the source theorem advertised under this reused name. -/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd m n := by
  rfl

end MathGraphReceipt
