import FiniteEnvelope

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


/-- A simultaneous write updates one symbol at the current position of
    every source work head. -/
def writeAllSource {w : ℕ} (tape : Fin w → ℤ → α)
    (head : Fin w → ℤ) (write : Fin w → α) :
    Fin w → ℤ → α :=
  fun k z => if z = head k then write k else tape k z

/-- The corresponding binary-track update writes the symbol block's bit
    on each track with the same source head coordinate. -/
def writeAllEncoded (e : α ≃ Fin K) (blank : α) {w : ℕ}
    (bits : Fin (w * K) → ℤ → Bool)
    (head : Fin w → ℤ) (write : Fin w → α) :
    Fin (w * K) → ℤ → Bool :=
  fun j z =>
    let pair := (finProdFinEquiv (m := w) (n := K)).symm j
    if z = head pair.1 then
      encodeSymbol e blank (write pair.1) pair.2
    else bits j z

/-- The complete simultaneous OAI-style write step COMMUTES exactly with
    finite-symbol encoding. This is an effective local simulation law;
    state transitions, head movements, coin bits and halting are separate. -/
theorem encodeTracks_writeAll_commutes (e : α ≃ Fin K) (blank : α)
    {w : ℕ} (tape : Fin w → ℤ → α)
    (head : Fin w → ℤ) (write : Fin w → α) :
    encodeTracks e blank (writeAllSource tape head write) =
      writeAllEncoded e blank (encodeTracks e blank tape) head write := by
  funext j z
  simp only [encodeTracks, writeAllSource, writeAllEncoded]
  split_ifs <;> rfl


/-- An independent finite-work-alphabet machine action, with the same
    finite-control, input and head movement dimensions as OAI's action. -/
structure SymbolAction (q w h : ℕ) where
  nextState : Fin (q + 1)
  write : Fin w → α
  workMove : Fin w → OAI.ExactDerandomization.Direction
  inputMove : Fin h → OAI.ExactDerandomization.Direction

/-- Compile one finite-symbol action to OAI's Boolean-work-tape action,
    duplicating each work-head movement across its K binary tracks. -/
def lowerAction (e : α ≃ Fin K) (blank : α)
    {q w h : ℕ} (a : SymbolAction (α := α) q w h) :
    OAI.ExactDerandomization.Action q (w * K) h where
  nextState := a.nextState
  write := fun j =>
    let pair := (finProdFinEquiv (m := w) (n := K)).symm j
    encodeSymbol e blank (a.write pair.1) pair.2
  workMove := fun j =>
    let pair := (finProdFinEquiv (m := w) (n := K)).symm j
    a.workMove pair.1
  inputMove := a.inputMove

/-- Every output bit of the compiled write action equals the corresponding
    bit of the original finite-symbol write instruction. -/
theorem lowerAction_write_bit (e : α ≃ Fin K) (blank : α)
    {q w h : ℕ} (a : SymbolAction (α := α) q w h)
    (k : Fin w) (i : Fin K) :
    (lowerAction e blank a).write
      (finProdFinEquiv (m := w) (n := K) (k, i)) =
        encodeSymbol e blank (a.write k) i := by
  have hpair :
      (finProdFinEquiv (m := w) (n := K)).symm
        (finProdFinEquiv (k, i)) = (k, i) :=
    Equiv.symm_apply_apply _ _
  simpa [lowerAction, hpair]

/-- All Boolean tracks for a source work head carry its same direction. -/
theorem lowerAction_group_move (e : α ≃ Fin K) (blank : α)
    {q w h : ℕ} (a : SymbolAction (α := α) q w h)
    (k : Fin w) (i : Fin K) :
    (lowerAction e blank a).workMove
      (finProdFinEquiv (m := w) (n := K) (k, i)) = a.workMove k := by
  have hpair :
      (finProdFinEquiv (m := w) (n := K)).symm
        (finProdFinEquiv (k, i)) = (k, i) :=
    Equiv.symm_apply_apply _ _
  simpa [lowerAction, hpair]

/-- A lockstep Boolean-head copy commutes with the unit movement rule. -/
theorem copyHeadMovement_commutes {w : ℕ}
    (head : Fin w → ℤ) (movement : Fin w → OAI.ExactDerandomization.Direction) :
    (fun j : Fin (w * K) =>
      let pair := (finProdFinEquiv (m := w) (n := K)).symm j
      (movement pair.1).move (head pair.1)) =
    (fun j : Fin (w * K) =>
      let pair := (finProdFinEquiv (m := w) (n := K)).symm j
      ((fun k => (movement k).move (head k)) pair.1)) := by
  rfl

end Metalogic.OpenAIMath.ExplicitAlphabetBridge
