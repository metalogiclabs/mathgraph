import VerifiedDevelopmentalNavigation

namespace VerifiedDevelopmentalNavigation.PalomarSeed

/-!
A direct VDN instantiation of the finite closure-capability witness submitted to
Palomar. This file keeps the witness tiny: old capability = rotation plus
LT→LE; extended capability additionally admits AND→OR.
-/

inductive Token where
  | LT | LE | AND | OR | A | B
  deriving DecidableEq, Repr

inductive Pos where
  | p0 | p1 | p2 | p3
  deriving DecidableEq, Repr

abbrev State := Pos → Token

private def pred : Pos → Pos
  | .p0 => .p3
  | .p1 => .p0
  | .p2 => .p1
  | .p3 => .p2

private def rotate (s : State) : State := fun p => s (pred p)

private def replaceAt (p : Pos) (src dst : Token) (s : State) : State :=
  fun q => if q = p then if s q = src then dst else s q else s q

inductive OldAction where
  | rot
  | ltle (p : Pos)
  deriving DecidableEq, Repr

inductive NewAction where
  | rot
  | ltle (p : Pos)
  | andor (p : Pos)
  deriving DecidableEq, Repr

private def oldStep : OldAction → State → Option State
  | .rot, s => some (rotate s)
  | .ltle p, s => some (replaceAt p .LT .LE s)

private def newStep : NewAction → State → Option State
  | .rot, s => some (rotate s)
  | .ltle p, s => some (replaceAt p .LT .LE s)
  | .andor p, s => some (replaceAt p .AND .OR s)

/-- Coordinate observations make token-level consequences verifier-visible. -/
def oldWorld : World State Pos OldAction Token where
  observe p s := s p
  step := oldStep

def newWorld : World State Pos NewAction Token where
  observe p s := s p
  step := newStep

def start : State
  | .p0 => .A
  | .p1 => .LT
  | .p2 => .B
  | .p3 => .AND

def afterO1 : State
  | .p0 => .A
  | .p1 => .LE
  | .p2 => .B
  | .p3 => .AND

def target : State
  | .p0 => .A
  | .p1 => .LE
  | .p2 => .B
  | .p3 => .OR

/-- Generic VDN reachability: a target is reachable when some admitted finite
action trace executes to it. -/
def ReachBy {X C A O : Type} (W : World X C A O) (x y : X) : Prop :=
  ∃ trace : List A, W.run trace x = some y

private def NoOR (s : State) : Prop := ∀ p, s p ≠ .OR

private theorem noOR_rotate {s : State} (h : NoOR s) : NoOR (rotate s) := by
  intro p
  exact h (pred p)

private theorem noOR_ltle {s : State} (p : Pos) (h : NoOR s) :
    NoOR (replaceAt p .LT .LE s) := by
  intro q
  by_cases hqp : q = p
  · subst q
    by_cases hs : s p = .LT
    · simp [replaceAt, hs]
    · simp [replaceAt, hs, h p]
  · simp [replaceAt, hqp, h q]

private theorem oldRun_preserves_noOR (trace : List OldAction) {s t : State}
    (hrun : oldWorld.run trace s = some t) (h : NoOR s) : NoOR t := by
  induction trace generalizing s t with
  | nil =>
      simp at hrun
      subst t
      exact h
  | cons a as ih =>
      cases a with
      | rot =>
          have hrun' : oldWorld.run as (rotate s) = some t := by
            simpa [World.run, oldWorld, oldStep] using hrun
          exact ih hrun' (noOR_rotate h)
      | ltle p =>
          have hrun' : oldWorld.run as (replaceAt p .LT .LE s) = some t := by
            simpa [World.run, oldWorld, oldStep] using hrun
          exact ih hrun' (noOR_ltle p h)

/-- The protected target is outside the old admitted continuation closure. -/
theorem old_closure_obstruction : ¬ ReachBy oldWorld start target := by
  intro h
  rcases h with ⟨trace, hrun⟩
  have hno : NoOR target := oldRun_preserves_noOR trace hrun (by
    intro p
    cases p <;> decide)
  exact hno .p3 rfl

/-- Adjoining AND→OR makes the target reachable by an explicit two-step
continuation. -/
theorem extended_closure_reaches_target : ReachBy newWorld start target := by
  have e1 : replaceAt .p1 .LT .LE start = afterO1 := by
    funext p
    cases p <;> rfl
  have e2 : replaceAt .p3 .AND .OR afterO1 = target := by
    funext p
    cases p <;> rfl
  refine ⟨[.ltle .p1, .andor .p3], ?_⟩
  simp [World.run, newWorld, newStep, e1, e2]

/-- The seed exhibits a strict verified capability phase change: unreachable
under the old continuation language and reachable under its extension. -/
theorem strict_verified_capability_growth :
    (¬ ReachBy oldWorld start target) ∧ ReachBy newWorld start target := by
  exact ⟨old_closure_obstruction, extended_closure_reaches_target⟩

end VerifiedDevelopmentalNavigation.PalomarSeed
