/- Frozen comparator challenge for an externally authored Lean core theorem.
   Original: leanprover/lean4 v4.35.0, src/Init/Data/Nat/Gcd.lean,
   Nat.gcd_comm (Git blob 6b3ac409cc1ed8775644c5c6a00a1a59f96fac2b).
   The intentional sorry is ONLY in the challenge statement, never in Solution.
-/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m := by
  sorry

end MathGraphReceipt
