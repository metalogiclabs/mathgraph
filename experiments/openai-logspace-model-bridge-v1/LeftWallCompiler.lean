import LeftBoundedMachine

/-!
# Left-end-marker compiler into the exact pinned OAI Boolean machine

The target has two synchronous Boolean work heads: content (track 0)
and a persistent origin marker (track 1). A fresh start state writes the
marker at coordinate zero before executing any source transition. The target
therefore has an explicit one-step startup overhead; its ordinary active
transitions use the marker to saturate left movement at zero.
-/

namespace Metalogic.OpenAIMath.LeftWallCompiler

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine

variable {q h n : ℕ}

def activeState (st : Fin (q + 1)) : Fin (q + 2) :=
  ⟨st.val, by omega⟩

def startupState (q : ℕ) : Fin (q + 2) :=
  ⟨q + 1, by omega⟩

def decodeActive (st : Fin (q + 2)) : Option (Fin (q + 1)) :=
  if hh : st.val < q + 1 then some ⟨st.val, hh⟩ else none

theorem decodeActive_active (st : Fin (q + 1)) :
    decodeActive (activeState st) = some st := by
  have hs := st.isLt
  simp [decodeActive, activeState, hs]

theorem decodeActive_startup (q : ℕ) :
    decodeActive (startupState q) = none := by
  simp [decodeActive, startupState]

/-- Source configurations are represented with nonnegative OAI coordinates
and a second, permanent, true-at-zero marker track. -/
def encode (c : LeftConfiguration q h n) : Configuration (q + 1) 2 h n where
  state := activeState c.state
  inputPos := c.inputPos
  workPos := fun _ => (c.workPos : ℤ)
  work := fun j z => if j.val = 0 then extendWork c.work z else marker z

/-- A total compiler. In its special start state it writes the origin marker.
In active states it reads this marker to simulate left-end clamping exactly. -/
def compile (M : LeftMachine q h) : Machine (q + 1) 2 h where
  initialState := startupState q
  output := fun st =>
    match decodeActive st with
    | none => none
    | some sourceState => M.output sourceState
  transition := fun st inp read coin =>
    match decodeActive st with
    | none =>
      { nextState := activeState M.initialState
        write := fun j => decide (j.val = 1)
        workMove := fun _ => .stay
        inputMove := fun _ => .stay }
    | some sourceState =>
      let a := M.transition sourceState inp (read 0) coin
      { nextState := activeState a.nextState
        write := fun j => if j.val = 0 then a.write else read 1
        workMove := fun _ => guardedMove a.workMove (read 1)
        inputMove := a.inputMove }

theorem compile_output_active (M : LeftMachine q h)
    (st : Fin (q + 1)) :
    (compile M).output (activeState st) = M.output st := by
  simp [compile, decodeActive_active]

theorem compile_output_startup (M : LeftMachine q h) :
    (compile M).output (startupState q) = none := by
  simp [compile, decodeActive_startup]

theorem encode_work_read (c : LeftConfiguration q h n) :
    (encode c).work (0 : Fin 2) ((encode c).workPos 0) =
      c.work c.workPos := by
  simp [encode, extendWork]

theorem encode_marker_read (c : LeftConfiguration q h n) :
    (encode c).work (1 : Fin 2) ((encode c).workPos 1) =
      marker (c.workPos : ℤ) := by
  simp [encode]

/-- A marker is never destroyed by rewriting its currently read value. -/
theorem marker_rewrite_id (z : ℤ) :
    Function.update marker z (marker z) = marker := by
  funext p
  by_cases heq : p = z
  · subst p
    simp [Function.update]
  · simp [Function.update, heq]

/-- The active OAI head step coincides with the source's left-bounded
head step under the permanent-origin-marker encoding. -/
theorem encoded_head_motion (c : LeftConfiguration q h n)
    (d : Direction) :
    (guardedMove d
        ((encode c).work (1 : Fin 2) ((encode c).workPos 1))).move
        ((encode c).workPos 0) =
      (moveNat d c.workPos : ℤ) := by
  simpa only [encode_marker_read] using guardedMove_correct d c.workPos

/-- The OAI target initializes its marker in one physical transition,
even though the native source machine starts with an all-blank Nat tape. -/
theorem bootstrap_marker_written (M : LeftMachine q h)
    (x : Word) (coin : Bool) :
    ((compile M).step x coin ((compile M).initial x.length)).work
      (1 : Fin 2) (0 : ℤ) = true := by
  simp [Machine.step, Machine.initial, compile,
    decodeActive_startup, startupState, Function.update]

theorem bootstrap_enters_active_state (M : LeftMachine q h)
    (x : Word) (coin : Bool) :
    ((compile M).step x coin ((compile M).initial x.length)).state =
      activeState M.initialState := by
  simp [Machine.step, Machine.initial, compile,
    decodeActive_startup, startupState]

theorem bootstrap_heads_at_origin (M : LeftMachine q h)
    (x : Word) (coin : Bool) (j : Fin 2) :
    ((compile M).step x coin ((compile M).initial x.length)).workPos j =
      (0 : ℤ) := by
  simp [Machine.step, Machine.initial, compile,
    decodeActive_startup, startupState, Direction.move]

/-- Extend-source-write commutation is the essential tape-frame condition:
a source write on Nat equals a target write on the nonnegative Int half-tape. -/
theorem extendWork_update (f : ℕ → Bool) (p : ℕ) (b : Bool) :
    extendWork (Function.update f p b) =
      Function.update (extendWork f) (p : ℤ) b := by
  funext z
  by_cases hn : z < 0
  · have hne : z ≠ (p : ℤ) := by omega
    simp [extendWork, Function.update, hn, hne]
  · by_cases heq : z = (p : ℤ)
    · subst z
      simp [extendWork, Function.update]
    · have hnat : z.toNat ≠ p := by omega
      simp [extendWork, Function.update, hn, heq, hnat]

end Metalogic.OpenAIMath.LeftWallCompiler
