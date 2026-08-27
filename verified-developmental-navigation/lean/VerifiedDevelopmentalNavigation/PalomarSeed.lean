import VerifiedDevelopmentalNavigation

namespace VerifiedDevelopmentalNavigation.PalomarSeed

/-!
A direct VDN instantiation of the finite closure-capability witness submitted to
Palomar.  This file deliberately keeps the witness tiny: old capability =
rotation plus LT→LE; extended capability additionally admits AND→OR.

The point is not to re-prove every Palomar packaging theorem.  It is to show
that the same witness is literally an instance of the generic verified-future
and verified-reachability core.
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

/-- Coordinate observations make every token-level consequence externally
visible to the verifier. -/
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

/-- Generic VDN reachability: a target is reachable when some finite admitted
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

private theorem oldStep_preserves_noOR (a : OldAction) {s t : State}
    (hstep : oldStep a s = some t) (h : NoOR s) : NoOR t := by
  cases a with
  | rot =>
      simp [oldStep] at hstep
      subst t
      exact noOR_rotate h
  | ltle p =>
      simp [oldStep] at hstep
      subst t
      exact noOR_ltle p h

private theorem oldRun_preserves_noOR (trace : List OldAction) {s t : State}
    (hrun : oldWorld.run trace s = some t) (h : NoOR s) : NoOR t := by
  induction trace generalizing s t with
  | nil =>
      simp at hrun
      subst t
      exact h
  | cons a as ih =>
      simp [World.run] at hrun
      cases hs : oldStep a s with
      | none => simp [hs] at hrun
      | some u =>
          have hu : NoOR u := oldStep_preserves_noOR a hs h
          exact ih hrun hu

/-- Palomar's negative half, now stated directly in the generic VDN reachability
language: the protected target is outside the old admitted continuation closure. -/
theorem old_closure_obstruction : ¬ ReachBy oldWorld start target := by
  intro h
  rcases h with ⟨trace, hrun⟩
  have hno : NoOR target := oldRun_preserves_noOR trace hrun (by
    intro p
    cases p <;> decide)
  exact hno .p3 rfl

/-- Palomar's positive half, now in VDN form: adjoining AND→OR makes the target
reachable by an explicit two-step continuation. -/
theorem extended_closure_reaches_target : ReachBy newWorld start target := by
  refine ⟨[.ltle .p1, .andor .p3], ?_⟩
  rfl

/-- The seed therefore exhibits a strict verified capability phase change:
unreachable in the old continuation language, reachable in the extension. -/
theorem strict_verified_capability_growth :
    (¬ ReachBy oldWorld start target) ∧ ReachBy newWorld start target := by
  exact ⟨old_closure_obstruction, extended_closure_reaches_target⟩

end VerifiedDevelopmentalNavigation.PalomarSeed
