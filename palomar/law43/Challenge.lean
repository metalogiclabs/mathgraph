import equational_theories.Definability.Basic
import equational_theories.Equations.All

open Law
open Law.MagmaLaw

/-!
# Swapped-arguments laws define commutativity

This is the advertised statement surface for the MathGraph Palomar candidate.
It states a structural universal-algebra result over magmas: whenever a two-variable
law has a right-hand side obtained from its left-hand side by swapping the two
variables, every magma satisfying that law admits a term-defined commutative
binary operation.
-/

namespace MathGraphPalomar

/--
For any magma law `L` whose variables are among `0,1` and whose right-hand side is
obtained from the left-hand side by swapping `0` and `1`, the commutative law
`x ◇ y = y ◇ x` is term-definable from `L`.
-/
theorem main_result {L : NatMagmaLaw}
    (hL2args : ∀ e ∈ L.lhs.elems.1, e ∈ [0,1] := by decide +kernel)
    (_hR2args : ∀ e ∈ L.rhs.elems.1, e ∈ [0,1] := by decide +kernel)
    (hSymm : L.lhs ⬝ (fun x ↦ Lf $ Equiv.swap 0 1 x) = L.rhs := by rfl) :
    Law43.TermDefinableFrom L := by
  sorry

end MathGraphPalomar
