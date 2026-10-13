/- Deliberately unauthorized axiom. This compiles as ordinary Lean
   source, but comparator must REJECT because permitted axioms are only
   the standard three (propext, Quot.sound, Classical.choice).
-/
import Init.Data.Nat.Gcd

namespace MathGraphReceipt

axiom injected_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m

theorem upstream_gcd_comm (m n : Nat) : Nat.gcd m n = Nat.gcd n m :=
  injected_gcd_comm m n

end MathGraphReceipt
