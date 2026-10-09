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


/-- For a designated tape blank, use an all-zero block, not a one-hot blank.
    This is necessary to preserve infinite untouched blank tape regions. -/
def encodeSymbolWithBlank (blank a : α) (i : Fin (Fintype.card α)) : Bool :=
  decide (a ≠ blank ∧ i = Fintype.equivFin α a)

theorem encodeBlank_is_zero (blank : α) :
    encodeSymbolWithBlank blank blank = fun _ => false := by
  funext i
  simp [encodeSymbolWithBlank]

theorem encodeNonblank_true_at_index
    (blank a : α) (ha : a ≠ blank) :
    encodeSymbolWithBlank blank a (Fintype.equivFin α a) = true := by
  simp [encodeSymbolWithBlank, ha]

theorem encodeSymbolWithBlank_injective (blank : α) :
    Function.Injective (encodeSymbolWithBlank (α := α) blank) := by
  intro a b heq
  by_cases ha : a = blank
  · subst a
    by_cases hb : b = blank
    · exact hb.symm
    · have hpoint := congrArg
        (fun f : Fin (Fintype.card α) → Bool =>
          f (Fintype.equivFin α b)) heq
      have hfalse : False := by
        simpa [encodeSymbolWithBlank, hb] using hpoint
      exact hfalse.elim
  · by_cases hb : b = blank
    · subst b
      have hpoint := congrArg
        (fun f : Fin (Fintype.card α) → Bool =>
          f (Fintype.equivFin α a)) heq
      have hfalse : False := by
        simpa [encodeSymbolWithBlank, ha] using hpoint
      exact hfalse.elim
    · have hpoint := congrArg
        (fun f : Fin (Fintype.card α) → Bool =>
          f (Fintype.equivFin α a)) heq
      have hindex : Fintype.equivFin α a = Fintype.equivFin α b := by
        simpa [encodeSymbolWithBlank, ha, hb] using hpoint
      exact (Fintype.equivFin α).injective hindex

/-- Changing a finite-symbol tape's blank default into an all-zero
    Boolean-block tape retains equality and distinguishability of cells. -/
theorem encodeBlankWorkTapes_injective (w : ℕ) (blank : α) :
    Function.Injective
      (fun tape : Fin w → ℤ → α =>
        fun k z i => encodeSymbolWithBlank blank (tape k z) i) := by
  intro tape other heq
  funext k z
  apply encodeSymbolWithBlank_injective blank
  funext i
  exact congrFun (congrFun (congrFun heq k) z) i


/-- Convert w finite-alphabet tapes into a fixed number w·|α| of Boolean
    tapes, using one Boolean track per alphabet symbol. The number of tracks
    is constant for any fixed source machine, independent of input length. -/
def encodeWorkTapesAsBoolean {w : ℕ} (blank : α)
    (tape : Fin w → ℤ → α) :
    Fin (w * Fintype.card α) → ℤ → Bool :=
  fun j z =>
    let pair := (finProdFinEquiv (m := w) (n := Fintype.card α)).symm j
    encodeSymbolWithBlank blank (tape pair.1 z) pair.2

/-- No information is lost by the constant-number-of-Boolean-tracks map. -/
theorem encodeWorkTapesAsBoolean_injective
    (w : ℕ) (blank : α) :
    Function.Injective (encodeWorkTapesAsBoolean (w := w) blank) := by
  intro tape other heq
  funext k z
  apply encodeSymbolWithBlank_injective blank
  funext i
  have hbit := congrFun
    (congrFun heq ((finProdFinEquiv (m := w) (n := Fintype.card α)) (k, i))) z
  simpa [encodeWorkTapesAsBoolean] using hbit

/-- An initially blank exterior stays represented by all-false Boolean bits,
    without introducing infinite nonblank support on additional tracks. -/
theorem encodeWorkTapesAsBoolean_blank_outside
    {w : ℕ} (blank : α) (tape : Fin w → ℤ → α) (s : ℕ)
    (hblank : ∀ k z, (s : ℤ) < |z| → tape k z = blank)
    (j : Fin (w * Fintype.card α)) (z : ℤ)
    (hz : (s : ℤ) < |z|) :
    encodeWorkTapesAsBoolean blank tape j z = false := by
  simp [encodeWorkTapesAsBoolean, hblank _ z hz, encodeSymbolWithBlank]

end Metalogic.OpenAIMath.AlphabetBridge
