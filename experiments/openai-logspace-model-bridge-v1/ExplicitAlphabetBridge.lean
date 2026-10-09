import Mathlib

/-!
Executable finite-alphabet to Boolean-track encoding, parameterized by an
explicit enumeration equivalence. This makes the encoding effective for a
fixed finite alphabet with a supplied lookup table, rather than relying on
the noncomputable Fintype.equivFin choice.
-/

namespace Metalogic.OpenAIMath.ExplicitAlphabetBridge

variable {α : Type} [DecidableEq α] {K : ℕ}

/-- The source supplies its concrete, reversible symbol-to-index enumeration.
    The blank symbol is encoded as the all-zero Boolean block. -/
def encodeSymbol (e : α ≃ Fin K) (blank a : α) (i : Fin K) : Bool :=
  decide (a ≠ blank ∧ i = e a)

theorem blank_is_all_zero (e : α ≃ Fin K) (blank : α) :
    encodeSymbol e blank blank = fun _ => false := by
  funext i
  simp [encodeSymbol]

theorem nonblank_has_set_bit
    (e : α ≃ Fin K) (blank a : α) (ha : a ≠ blank) :
    encodeSymbol e blank a (e a) = true := by
  simp [encodeSymbol, ha]

theorem encodeSymbol_injective (e : α ≃ Fin K) (blank : α) :
    Function.Injective (encodeSymbol e blank) := by
  intro a b heq
  by_cases ha : a = blank
  · subst a
    by_cases hb : b = blank
    · exact hb.symm
    · have point := congrArg (fun f : Fin K → Bool => f (e b)) heq
      have absurd : False := by simpa [encodeSymbol, hb] using point
      exact absurd.elim
  · by_cases hb : b = blank
    · subst b
      have point := congrArg (fun f : Fin K → Bool => f (e a)) heq
      have absurd : False := by simpa [encodeSymbol, ha] using point
      exact absurd.elim
    · have point := congrArg (fun f : Fin K → Bool => f (e a)) heq
      have idx : e a = e b := by
        simpa [encodeSymbol, ha, hb] using point
      exact e.injective idx

/-- w alphabet tapes are represented on w*K binary tracks, independent of
    input length. A complete transition-by-transition compiler is separate. -/
def encodeTracks (e : α ≃ Fin K) (blank : α) {w : ℕ}
    (tape : Fin w → ℤ → α) : Fin (w * K) → ℤ → Bool :=
  fun j z =>
    let pair := (finProdFinEquiv (m := w) (n := K)).symm j
    encodeSymbol e blank (tape pair.1 z) pair.2

theorem encodeTracks_injective (e : α ≃ Fin K) (blank : α) (w : ℕ) :
    Function.Injective (encodeTracks (w := w) e blank) := by
  intro tape other h
  funext k z
  apply encodeSymbol_injective e blank
  funext i
  have bit := congrFun
    (congrFun h ((finProdFinEquiv (m := w) (n := K)) (k, i))) z
  simpa [encodeTracks] using bit

/-- A blank exterior on the source tape becomes an all-false exterior on
    every binary track at the same spatial radius. -/
theorem encodeTracks_blank_outside (e : α ≃ Fin K) (blank : α) {w : ℕ}
    (tape : Fin w → ℤ → α) (s : ℕ)
    (hblank : ∀ k z, (s : ℤ) < |z| → tape k z = blank)
    (j : Fin (w * K)) (z : ℤ) (hz : (s : ℤ) < |z|) :
    encodeTracks (w := w) e blank tape j z = false := by
  simp [encodeTracks, hblank _ z hz, encodeSymbol]

end Metalogic.OpenAIMath.ExplicitAlphabetBridge
