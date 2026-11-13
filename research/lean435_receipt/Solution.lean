/- Reuse of the original theorem from upstream Lean 4.35.0.
   This wrapper is NOT a new mathematical discovery and does not
   independently reconstruct the upstream original proof.
-/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m :=
  Nat.gcd_comm m n

end MathGraphReceipt
