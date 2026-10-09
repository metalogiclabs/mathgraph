import LeftWallFusedCompiler

/-!
# Active-step exact semantics of the left-bounded source / OAI target

The source has a Nat-indexed tape and saturating left move, while the target
has two integer-indexed Boolean work heads. Prove agreement on already
encoded configurations independently of the fused startup case.
-/

namespace Metalogic.OpenAIMath.LeftWallActiveStep

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftBoundedMachine
open Metalogic.OpenAIMath.LeftWallCompiler
open Metalogic.OpenAIMath.LeftWallFusedCompiler

variable {q h : ℕ}

theorem configuration_ext_fields
    {n : ℕ} (a b : Configuration (q + 1) 2 h n)
    (hs : a.state = b.state) (hi : a.inputPos = b.inputPos)
    (hp : a.workPos = b.workPos) (hw : a.work = b.work) : a = b := by
  cases a
  cases b
  cases hs
  cases hi
  cases hp
  cases hw
  rfl

/-- An OAI transition out of an encoded active state implements exactly
one source transition, including all infinite tape-cell observations. -/
theorem active_step_commutes (M : LeftMachine q h)
    (x : Word) (coin : Bool) (c : LeftConfiguration q h x.length) :
    (compileFused M).step x coin (encode c) =
      encode (LeftBoundedMachine.step M x coin c) := by
  cases ho : M.output c.state with
  | some b =>
      simp [Machine.step, LeftBoundedMachine.step,
        encode, compileFused, decodeActive_active, ho]
  | none =>
      apply configuration_ext_fields
      · simp [Machine.step, LeftBoundedMachine.step,
          encode, compileFused, decodeActive_active, ho,
          extendWork_nat]
      · funext j
        simp [Machine.step, LeftBoundedMachine.step,
          encode, compileFused, decodeActive_active, ho,
          extendWork_nat]
      · funext j
        fin_cases j <;>
          simp [Machine.step, LeftBoundedMachine.step,
            encode, compileFused, decodeActive_active, ho,
            extendWork_nat, guardedMove_correct]
      · funext j z
        fin_cases j
        · simpa [Machine.step, LeftBoundedMachine.step,
            encode, compileFused, decodeActive_active, ho,
            extendWork_nat] using
            congrFun
              (LeftWallCompiler.extendWork_update c.work c.workPos
                ((M.transition c.state
                  (fun k => readInput x (c.inputPos k))
                  (c.work c.workPos) coin).write)).symm z
        · simpa [Machine.step, LeftBoundedMachine.step,
            encode, compileFused, decodeActive_active, ho,
            extendWork_nat] using
            congrFun (LeftWallCompiler.marker_rewrite_id
              (c.workPos : ℤ)) z

end Metalogic.OpenAIMath.LeftWallActiveStep
