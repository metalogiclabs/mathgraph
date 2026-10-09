import BooleanProbabilisticClassBridge

/-!
# Independently specified one-tape left-bounded machine

The work tape is indexed by Nat, and left movement at zero stays at zero.
This differs from pinned OAI machines' bi-infinite integer tape coordinate.
Input, finite control, and coin interface are kept common intentionally.
-/

namespace Metalogic.OpenAIMath.LeftBoundedMachine

open OAI.ExactDerandomization

structure LeftAction (q h : ℕ) where
  nextState : Fin (q + 1)
  write : Bool
  workMove : Direction
  inputMove : Fin h → Direction

structure LeftMachine (q h : ℕ) where
  initialState : Fin (q + 1)
  output : Fin (q + 1) → Option Bool
  transition : Fin (q + 1) → (Fin h → InputSymbol) → Bool → Bool →
    LeftAction q h

structure LeftConfiguration (q h n : ℕ) where
  state : Fin (q + 1)
  inputPos : Fin h → Fin (n + 2)
  workPos : ℕ
  work : ℕ → Bool

/-- Saturating left motion at the natural-number tape origin. -/
def moveNat (d : Direction) (z : ℕ) : ℕ :=
  match d with
  | .left => z - 1
  | .stay => z
  | .right => z + 1

def initial (M : LeftMachine q h) (n : ℕ) :
    LeftConfiguration q h n where
  state := M.initialState
  inputPos := fun _ => ⟨0, by omega⟩
  workPos := 0
  work := fun _ => false

def step (M : LeftMachine q h) (x : Word) (coin : Bool)
    (c : LeftConfiguration q h x.length) :
    LeftConfiguration q h x.length :=
  match M.output c.state with
  | some _ => c
  | none =>
      let a := M.transition c.state
        (fun j => readInput x (c.inputPos j)) (c.work c.workPos) coin
      { state := a.nextState
        inputPos := fun j => (a.inputMove j).moveInput (c.inputPos j)
        workPos := moveNat a.workMove c.workPos
        work := Function.update c.work c.workPos a.write }

def run (M : LeftMachine q h) (x : Word) (coins : CoinTape) :
    ℕ → LeftConfiguration q h x.length
  | 0 => initial M x.length
  | t + 1 => step M x (coins t) (run M x coins t)

/-- True only at coordinate zero: a boundary marker independent of tape data. -/
def marker (z : ℤ) : Bool := decide (z = 0)

/-- Embed a natural-number tape in the nonnegative half of an OAI integer tape. -/
def extendWork (work : ℕ → Bool) (z : ℤ) : Bool :=
  if z < 0 then false else work z.toNat

theorem extendWork_nat (work : ℕ → Bool) (z : ℕ) :
    extendWork work (z : ℤ) = work z := by
  simp [extendWork]

theorem extendWork_negative (work : ℕ → Bool) (z : ℤ)
    (hz : z < 0) : extendWork work z = false := by
  simp [extendWork, hz]

/-- Core geometry law: when a marker at zero prevents crossing to negative
coordinates, the OAI integer move matches saturated Nat movement exactly. -/
def guardedMove (d : Direction) (atBoundary : Bool) : Direction :=
  if atBoundary && (d == .left) then .stay else d

theorem guardedMove_correct (d : Direction) (z : ℕ) :
    (guardedMove d (marker (z : ℤ))).move (z : ℤ) =
      (moveNat d z : ℤ) := by
  cases d <;> cases z <;>
    simp [guardedMove, marker, moveNat, Direction.move] <;> omega

theorem marker_nat_zero_iff (z : ℕ) :
    marker (z : ℤ) = true ↔ z = 0 := by
  simp [marker]

/-- Exact time-indexed source space; one tape contributes the number of
distinct head positions visited, including time zero. -/
def spaceThrough (M : LeftMachine q h)
    (x : Word) (coins : CoinTape) (t : ℕ) : ℕ :=
  ((Finset.range (t + 1)).image (fun u => (run M x coins u).workPos)).card

end Metalogic.OpenAIMath.LeftBoundedMachine
