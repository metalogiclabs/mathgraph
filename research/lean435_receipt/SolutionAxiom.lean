/- Deliberately unauthorized axiom. This compiles as ordinary Lean
   source, but comparator must REJECT under permitted_axioms = [].
-/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

axiom injected_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m :=
  injected_gcd_comm m n

end MathGraphReceipt
