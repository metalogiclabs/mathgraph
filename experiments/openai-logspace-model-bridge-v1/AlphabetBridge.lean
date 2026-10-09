import FiniteEnvelope

/-!
A separately authored, fixed-width encoding of arbitrary finite machine
alphabets into Boolean work cells. This checks a necessary model-adequacy
ingredient; it does not construct a complete Turing-machine compiler.
-/

namespace Metalogic.OpenAIMath.AlphabetBridge

variable {α : Type} [Fintype α] [DecidableEq α]

/-- One-hot encoding uses a number of Boolean cells fixed by the alphabet,
not by the input length. -/
def encodeSymbol (a : α) : Fin (Fintype.card α) → Bool :=
  fun i => decide (i = Fintype.equivFin α a)

/-- Every finite symbol can be recovered uniquely from its Boolean block. -/
theorem encodeSymbol_injective :
    Function.Injective (encodeSymbol (α := α)) := by
  intro a b heq
  have hpoint := congrArg
    (fun bits : Fin (Fintype.card α) → Bool =>
      bits (Fintype.equivFin α a)) heq
  have hindex : Fintype.equivFin α a = Fintype.equivFin α b := by
    simpa [encodeSymbol] using hpoint
  exact (Fintype.equivFin α).injective hindex

/-- A valid symbol block has exactly one true bit, at the symbol's index. -/
theorem encodeSymbol_true_iff (a : α) (i : Fin (Fintype.card α)) :
    encodeSymbol a i = true ↔ i = Fintype.equivFin α a := by
  simp [encodeSymbol]

/-- Pointwise extension to multiple bi-infinite work tapes is injective. -/
theorem encodeWorkTapes_injective (w : ℕ) :
    Function.Injective
      (fun tape : Fin w → ℤ → α =>
        fun k z i => encodeSymbol (tape k z) i) := by
  intro tape other heq
  funext k z
  apply encodeSymbol_injective
  funext i
  exact congrFun (congrFun (congrFun heq k) z) i

/-- Recovering any tape cell from the same block proves original symbols equal. -/
theorem tape_cell_equal_of_bit_blocks_equal
    {w : ℕ} (a b : Fin w → ℤ → α) (k : Fin w) (z : ℤ)
    (h : ∀ i, encodeSymbol (a k z) i = encodeSymbol (b k z) i) :
    a k z = b k z := by
  apply encodeSymbol_injective
  funext i
  exact h i

end Metalogic.OpenAIMath.AlphabetBridge
