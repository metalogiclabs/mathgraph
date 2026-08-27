namespace VerifiedDevelopmentalNavigation

/-!
# Minimal verified future sufficiency

A small deterministic core for verified developmental navigation.

`World` supplies externally observable contexts and partial lawful actions.
Two states are future-equivalent exactly when every finite lawful action trace
has the same definedness and, whenever both traces survive, every protected
verifier observation agrees.

The central theorem is deliberately small: this relation is the greatest
(coarsest) relation preserving all protected verified futures. Any proposed
quotient relation with that preservation property refines `FutureEq`.
-/

structure World (X C A O : Type) where
  observe : C → X → O
  step : A → X → Option X

namespace World

variable {X C A O : Type} (W : World X C A O)

/-- Execute a finite action trace. -/
def run : List A → X → Option X
  | [], x => some x
  | a :: as, x =>
      match W.step a x with
      | none => none
      | some y => W.run as y

@[simp] theorem run_nil (x : X) : W.run [] x = some x := rfl

@[simp] theorem run_cons (a : A) (as : List A) (x : X) :
    W.run (a :: as) x = (W.step a x).bind (W.run as) := by
  cases h : W.step a x <;> simp [run, h]

/-- Two partial outcomes are observationally identical at context `c`.
Undefined must match undefined; surviving states must have equal verifier output. -/
def OutcomeEq (c : C) : Option X → Option X → Prop
  | none, none => True
  | some x, some y => W.observe c x = W.observe c y
  | _, _ => False

/-- States are equivalent exactly when every finite lawful continuation has the
same survival/definedness and the same protected verifier observations. -/
def FutureEq (x y : X) : Prop :=
  ∀ (trace : List A) (c : C), W.OutcomeEq c (W.run trace x) (W.run trace y)

@[refl] theorem futureEq_refl (x : X) : W.FutureEq x x := by
  intro trace c
  cases h : W.run trace x <;> simp [OutcomeEq, h]

@[symm] theorem futureEq_symm {x y : X} (hxy : W.FutureEq x y) : W.FutureEq y x := by
  intro trace c
  have h := hxy trace c
  cases hx : W.run trace x <;> cases hy : W.run trace y <;>
    simp [OutcomeEq, hx, hy] at h ⊢
  exact h.symm

@[trans] theorem futureEq_trans {x y z : X}
    (hxy : W.FutureEq x y) (hyz : W.FutureEq y z) : W.FutureEq x z := by
  intro trace c
  have h1 := hxy trace c
  have h2 := hyz trace c
  cases hx : W.run trace x <;> cases hy : W.run trace y <;> cases hz : W.run trace z <;>
    simp [OutcomeEq, hx, hy, hz] at h1 h2 ⊢
  exact h1.trans h2

/-- `FutureEq` is an equivalence relation and therefore defines a justified
quotient of histories/states. -/
theorem futureEq_equivalence : Equivalence W.FutureEq :=
  ⟨W.futureEq_refl, W.futureEq_symm, W.futureEq_trans⟩

/-- A relation is future-sufficient when identifying related states never
changes any protected verified consequence after any finite lawful trace. -/
def FutureSufficient (R : X → X → Prop) : Prop :=
  ∀ ⦃x y : X⦄, R x y →
    ∀ (trace : List A) (c : C), W.OutcomeEq c (W.run trace x) (W.run trace y)

/-- Minimal Verified Sufficient-State Theorem.

Every relation that is safe to quotient by with respect to all protected
verified futures refines `FutureEq`. Hence `FutureEq` is the greatest relation,
and its quotient is the coarsest state representation, preserving exactly those
future decisions. -/
theorem futureEq_greatest_future_sufficient
    {R : X → X → Prop} (hR : W.FutureSufficient R) :
    ∀ ⦃x y : X⦄, R x y → W.FutureEq x y := by
  intro x y hxy trace c
  exact hR hxy trace c

/-- The canonical relation is itself future-sufficient. -/
theorem futureEq_is_future_sufficient : W.FutureSufficient W.FutureEq := by
  intro x y hxy trace c
  exact hxy trace c

/-- Adding protected contexts can only split equivalence classes, never merge
previously distinguishable states. -/
def FutureEqOn (S : C → Prop) (x y : X) : Prop :=
  ∀ (trace : List A) ⦃c : C⦄, S c →
    W.OutcomeEq c (W.run trace x) (W.run trace y)

theorem context_refinement_monotone {S T : C → Prop}
    (hST : ∀ c, S c → T c) {x y : X}
    (hxy : W.FutureEqOn T x y) : W.FutureEqOn S x y := by
  intro trace c hc
  exact hxy trace (hST c hc)

/-- One verified separator immediately revokes an equivalence claim relative to
that context family. -/
theorem separator_forces_split {S : C → Prop} {x y : X}
    (trace : List A) (c : C) (hc : S c)
    (hsep : ¬ W.OutcomeEq c (W.run trace x) (W.run trace y)) :
    ¬ W.FutureEqOn S x y := by
  intro hxy
  exact hsep (hxy trace hc)

/-- A one-step recursive law: future-equivalent states cannot disagree about
whether an action survives; if both survive, the successors remain
future-equivalent. -/
theorem futureEq_step {x y : X} (hxy : W.FutureEq x y) (a : A) :
    (W.step a x = none ∧ W.step a y = none) ∨
    ∃ x' y', W.step a x = some x' ∧ W.step a y = some y' ∧ W.FutureEq x' y' := by
  cases hx : W.step a x with
  | none =>
      cases hy : W.step a y with
      | none => exact Or.inl ⟨hx, hy⟩
      | some y' =>
          exfalso
          have h := hxy [a] (Classical.choice (show Nonempty C from Classical.choice inferInstance))
          simp [run, hx, hy, OutcomeEq] at h
  | some x' =>
      cases hy : W.step a y with
      | none =>
          exfalso
          have h := hxy [a] (Classical.choice (show Nonempty C from Classical.choice inferInstance))
          simp [run, hx, hy, OutcomeEq] at h
      | some y' =>
          right
          refine ⟨x', y', hx, hy, ?_⟩
          intro trace c
          simpa [run, hx, hy] using hxy (a :: trace) c

end World

end VerifiedDevelopmentalNavigation
