import ModelSemantics

/-!
# Finite configuration envelope for the pinned OAI Logspace machine
A finite code for state, input heads, bounded work heads and bounded tape window.

This is a representation/counting lemma, not yet a polynomial-time bound:
the work-window radius must first be linked to the OAI spaceThrough measure.
-/

namespace Metalogic.OpenAIMath.FiniteEnvelope

open OAI.ExactDerandomization

/-- All data needed when work heads and nonblank cells lie in [-s,s]. -/
structure Envelope (q w h n s : ℕ) where
  state : Fin (q + 1)
  inputPos : Fin h → Fin (n + 2)
  workPos : Fin w → Fin (2 * s + 1)
  work : Fin w → Fin (2 * s + 1) → Bool
/-- A transparent equivalence to a product of finite function types. -/
def envelopeEquiv (q w h n s : ℕ) :
    Envelope q w h n s ≃
      Fin (q + 1) ×
        ((Fin h → Fin (n + 2)) ×
         ((Fin w → Fin (2 * s + 1)) ×
          (Fin w → Fin (2 * s + 1) → Bool))) where
  toFun e := ⟨e.state, ⟨e.inputPos, ⟨e.workPos, e.work⟩⟩⟩
  invFun t := {
    state := t.1
    inputPos := t.2.1
    workPos := t.2.2.1
    work := t.2.2.2
  }
  left_inv := by intro x; cases x; rfl
  right_inv := by intro x; rcases x with ⟨a,b,c,d⟩; rfl

noncomputable instance (q w h n s : ℕ) : Fintype (Envelope q w h n s) := by
  classical
  exact Fintype.ofEquiv _ (envelopeEquiv q w h n s).symm

/-- The bounded encoding state space is genuinely finite. -/
theorem envelope_finite (q w h n s : ℕ) :
    Finite (Envelope q w h n s) := inferInstance

/-- Cardinality of the finite envelope is an explicit combinatorial product. -/
theorem envelope_card (q w h n s : ℕ) :
    Fintype.card (Envelope q w h n s) =
      (q + 1) * (n + 2) ^ h * (2 * s + 1) ^ w *
        2 ^ (w * (2 * s + 1)) := by
  classical
  rw [Fintype.card_congr (envelopeEquiv q w h n s)]
  simp only [Fintype.card_prod, Fintype.card_fun, Fintype.card_fin, Fintype.card_bool]
  simp only [← pow_mul, mul_comm, mul_left_comm, mul_assoc]

/-- If two OAI configurations agree on their finite data and all tape cells
inside [-s,s] and are blank outside that interval, they are identical. -/
theorem configuration_ext_of_window
    {q w h n s : ℕ} (c d : Configuration q w h n)
    (hstate : c.state = d.state)
    (hinput : c.inputPos = d.inputPos)
    (hpositions : c.workPos = d.workPos)
    (hinside : ∀ k z, -(s : ℤ) ≤ z → z ≤ (s : ℤ) →
      c.work k z = d.work k z)
    (houtc : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      c.work k z = false)
    (houtd : ∀ k z, z < -(s : ℤ) ∨ (s : ℤ) < z →
      d.work k z = false) : c = d := by
  have hwork : c.work = d.work := by
    funext k z
    by_cases inside : -(s : ℤ) ≤ z ∧ z ≤ (s : ℤ)
    · exact hinside k z inside.1 inside.2
    · have outside : z < -(s : ℤ) ∨ (s : ℤ) < z := by omega
      rw [houtc k z outside, houtd k z outside]
  cases c
  cases d
  cases hstate
  cases hinput
  cases hpositions
  cases hwork
  rfl


/-- Unvisited work-tape cells remain blank in the exact OAI machine.
    A space-radius bound truncates memory only after proving displacement. -/
theorem unvisited_work_cell_is_blank
    {q w h : ℕ} (M : Machine q w h)
    (x : Word) (coins : CoinTape) (k : Fin w) (z : ℤ) (t : ℕ) :
    (∀ u, u < t → (M.run x coins u).workPos k ≠ z) →
      (M.run x coins t).work k z = false := by
  induction t with
  | zero =>
      intro _
      rfl
  | succ t ih =>
      intro hn
      have hearlier : (M.run x coins t).work k z = false :=
        ih (by
          intro u hu
          exact hn u (Nat.lt_trans hu (Nat.lt_succ_self t)))
      have hpos : (M.run x coins t).workPos k ≠ z :=
        hn t (Nat.lt_succ_self t)
      change (M.step x (coins t) (M.run x coins t)).work k z = false
      simp [Machine.step, hearlier, hpos, Ne.symm hpos]


/-- If a finite code uniquely represents every configuration occurring up to
    the first deterministic halt, the halting time is bounded by the number
    of possible codes. No encoding adequacy is assumed without proof. -/
theorem first_halt_lt_card_of_faithful_encoding
    {q w h : ℕ} {α : Type} [Fintype α]
    (M : Machine q w h) (hd : M.Deterministic)
    (x : Word) (coins : CoinTape) (H : ℕ) (answer : Bool)
    (halt : M.output (M.run x coins H).state = some answer)
    (before : ∀ j, j < H → M.output (M.run x coins j).state = none)
    (encode : Configuration q w h x.length → α)
    (faithful : ∀ t u, t ≤ H → u ≤ H →
      encode (M.run x coins t) = encode (M.run x coins u) →
      M.run x coins t = M.run x coins u) :
    H < Fintype.card α := by
  let f : Fin (H + 1) → α := fun i => encode (M.run x coins i.val)
  have hinj : Function.Injective f := by
    intro a b heq
    have heqc : M.run x coins a.val = M.run x coins b.val :=
      faithful a.val b.val (by omega) (by omega) heq
    by_cases hab : a.val < b.val
    · have hno :=
        ModelSemantics.no_configuration_repeat_before_first_halt
          M hd x coins H answer halt before a.val b.val hab (by omega)
      exact False.elim (hno heqc)
    by_cases hba : b.val < a.val
    · have hno :=
        ModelSemantics.no_configuration_repeat_before_first_halt
          M hd x coins H answer halt before b.val a.val hba (by omega)
      exact False.elim (hno heqc.symm)
    apply Fin.ext
    omega
  have hcard := Fintype.card_le_of_injective f hinj
  simp only [Fintype.card_fin] at hcard
  omega

end Metalogic.OpenAIMath.FiniteEnvelope
