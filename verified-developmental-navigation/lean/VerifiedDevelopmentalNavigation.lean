namespace VerifiedDevelopmentalNavigation

/-!
# Minimal verified future sufficiency

A deterministic kernel for verified developmental navigation.

A `World` supplies protected verifier observations and partial lawful actions.
Two states are future-equivalent when every finite lawful action trace has the
same definedness and, whenever both traces survive, every protected verifier
observation agrees.

The key design choice is that definedness is part of the future semantics even
when there are no observation contexts.  This makes lawful-continuation
identity independent of an accidental `Nonempty C` assumption.
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
      | some y => run as y

@[simp] theorem run_nil (x : X) : W.run [] x = some x := rfl

@[simp] theorem run_cons (a : A) (as : List A) (x : X) :
    W.run (a :: as) x = (W.step a x).bind (fun y => W.run as y) := by
  cases h : W.step a x <;> simp [run, h]

/-- Two partial outcomes have the same verified meaning.

Undefined must match undefined.  If both survive, every protected observation
must agree.  Mixed defined/undefined outcomes are always distinguishable. -/
def OutcomeEq : Option X → Option X → Prop
  | none, none => True
  | some x, some y => ∀ c : C, W.observe c x = W.observe c y
  | _, _ => False

/-- Restriction of outcome equivalence to an active protected context family.
Definedness remains protected even when the family is empty. -/
def OutcomeEqOn (S : C → Prop) : Option X → Option X → Prop
  | none, none => True
  | some x, some y => ∀ ⦃c : C⦄, S c → W.observe c x = W.observe c y
  | _, _ => False

/-- Verified future equivalence: every finite lawful continuation has the same
survival status and the same verifier-visible surviving consequence. -/
def FutureEq (x y : X) : Prop :=
  ∀ trace : List A, W.OutcomeEq (W.run trace x) (W.run trace y)

/-- Context-relative future equivalence. -/
def FutureEqOn (S : C → Prop) (x y : X) : Prop :=
  ∀ trace : List A, W.OutcomeEqOn S (W.run trace x) (W.run trace y)

theorem futureEq_refl (x : X) : W.FutureEq x x := by
  intro trace
  cases h : W.run trace x with
  | none => trivial
  | some z =>
      intro c
      rfl

theorem futureEq_symm {x y : X} (hxy : W.FutureEq x y) : W.FutureEq y x := by
  intro trace
  have h := hxy trace
  cases hx : W.run trace x <;> cases hy : W.run trace y <;>
    simp [OutcomeEq, hx, hy] at h ⊢
  intro c
  exact (h c).symm

theorem futureEq_trans {x y z : X}
    (hxy : W.FutureEq x y) (hyz : W.FutureEq y z) : W.FutureEq x z := by
  intro trace
  have h1 := hxy trace
  have h2 := hyz trace
  cases hx : W.run trace x <;> cases hy : W.run trace y <;> cases hz : W.run trace z <;>
    simp [OutcomeEq, hx, hy, hz] at h1 h2 ⊢
  intro c
  exact (h1 c).trans (h2 c)

/-- `FutureEq` is a genuine equivalence relation and therefore can serve as a
canonical quotient relation. -/
theorem futureEq_equivalence : Equivalence W.FutureEq :=
  ⟨W.futureEq_refl, W.futureEq_symm, W.futureEq_trans⟩

/-- The canonical setoid of verified futures. -/
def futureSetoid : Setoid X where
  r := W.FutureEq
  iseqv := W.futureEq_equivalence

/-- A relation is future-sufficient when quotienting by it cannot alter any
protected verified consequence after any finite lawful trace. -/
def FutureSufficient (R : X → X → Prop) : Prop :=
  ∀ ⦃x y : X⦄, R x y → W.FutureEq x y

/-- Minimal Verified Sufficient-State Theorem.

Every relation safe for quotienting with respect to all protected verified
futures refines `FutureEq`.  Thus `FutureEq` is the greatest safe relation and
its quotient is the coarsest safe state representation. -/
theorem futureEq_greatest_future_sufficient
    {R : X → X → Prop} (hR : W.FutureSufficient R) :
    ∀ ⦃x y : X⦄, R x y → W.FutureEq x y := by
  intro x y hxy
  exact hR hxy

/-- The canonical relation is itself future-sufficient. -/
theorem futureEq_is_future_sufficient : W.FutureSufficient W.FutureEq := by
  intro x y hxy
  exact hxy

/-- Adding protected contexts can only split equivalence classes, never merge
previously distinguishable states. -/
theorem context_refinement_monotone {S T : C → Prop}
    (hST : ∀ c, S c → T c) {x y : X}
    (hxy : W.FutureEqOn T x y) : W.FutureEqOn S x y := by
  intro trace
  have h := hxy trace
  cases hx : W.run trace x <;> cases hy : W.run trace y <;>
    simp [OutcomeEqOn, hx, hy] at h ⊢
  intro c hc
  exact h (hST c hc)

/-- One verified separator immediately revokes an equivalence claim relative to
that context family. -/
theorem separator_forces_split {S : C → Prop} {x y : X}
    (trace : List A)
    (hsep : ¬ W.OutcomeEqOn S (W.run trace x) (W.run trace y)) :
    ¬ W.FutureEqOn S x y := by
  intro hxy
  exact hsep (hxy trace)

/-- Future-equivalent states agree on one-step lawful-action definedness; if the
action survives, their successors remain future-equivalent. -/
theorem futureEq_step {x y : X} (hxy : W.FutureEq x y) (a : A) :
    (W.step a x = none ∧ W.step a y = none) ∨
    ∃ x' y', W.step a x = some x' ∧ W.step a y = some y' ∧ W.FutureEq x' y' := by
  cases hx : W.step a x with
  | none =>
      cases hy : W.step a y with
      | none => exact Or.inl ⟨hx, hy⟩
      | some y' =>
          exfalso
          have h := hxy [a]
          simp [run, hx, hy, OutcomeEq] at h
  | some x' =>
      cases hy : W.step a y with
      | none =>
          exfalso
          have h := hxy [a]
          simp [run, hx, hy, OutcomeEq] at h
      | some y' =>
          right
          refine ⟨x', y', hx, hy, ?_⟩
          intro trace
          simpa [run, hx, hy] using hxy (a :: trace)

/-- Every admitted action respects verified-future equivalence.  This is the
congruence fact needed to descend lawful actions to the quotient. -/
theorem step_respects_futureEq {x y : X} (hxy : W.FutureEq x y) (a : A) :
    match W.step a x, W.step a y with
    | none, none => True
    | some x', some y' => W.FutureEq x' y'
    | _, _ => False := by
  rcases W.futureEq_step hxy a with hnone | hsome
  · rcases hnone with ⟨hx, hy⟩
    simp [hx, hy]
  · rcases hsome with ⟨x', y', hx, hy, hxy'⟩
    simp [hx, hy, hxy']

end World

end VerifiedDevelopmentalNavigation
