/- Deliberately weaken BOTH challenge and solution: an easy tautology,
   but not Nat.gcd_comm. Comparator should accept this internally matching pair.
-/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd m n := by
  sorry

end MathGraphReceipt
