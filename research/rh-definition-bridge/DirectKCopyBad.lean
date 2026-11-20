import Lean

namespace Formalism.L2.Fam.KCopy

open Lean Meta Elab Tactic Term

def kdefeq (a b : Expr) : MetaM Bool := do
  let a ← instantiateMVars a
  let b ← instantiateMVars b
  if a.hasMVar || b.hasMVar then return false
  match Kernel.isDefEq (← getEnv) (← getLCtx) a b with
  | .ok r => return r
  | .error _ => return false

def ownStruct (env : Environment) (S : Name) : Bool :=
  isStructure env S && (S.getRoot == `Formalism || [``And, ``Prod, ``PProd, ``Sigma, ``PSigma, ``Subtype, ``Iff].contains S)

partial def copyAt (probe : Bool) (e tgt : Expr) (path : String) (fuel : Nat) : StateT (Array String) MetaM Expr := do
  let tgt ← instantiateMVars tgt
  let srcTy ← instantiateMVars (← inferType e)
  if srcTy == tgt then return e
  if fuel = 0 then
    modify (·.push path); return e
  let env ← getEnv

  if let .forallE n d b bi := tgt then
    return ← withLocalDecl n bi d fun x => do
      let body ← copyAt probe (mkApp e x) (b.instantiate1 x) (path ++ ".(" ++ toString n ++ ")") (fuel - 1)
      mkLambdaFVars #[x] body

  if let .const S us := tgt.getAppFn then
    if ownStruct env S then
      let ctor := getStructureCtor env S
      let fields := getStructureFields env S
      let mut acc := mkAppN (mkConst ctor.name us) (tgt.getAppArgs.extract 0 ctor.numParams)
      for i in [:fields.size] do
        let accTy ← whnf (← inferType acc)
        let .forallE _ fty _ bi := accTy | throwError "kcopy: constructor type of {S} is not a ∀"
        let p := Expr.proj S i e
        let v ← if bi.isInstImplicit then pure p else copyAt probe p fty (path ++ "." ++ toString fields[i]!) (fuel - 1)
        acc := mkApp acc v
      return acc

  if !probe then return e
  if ← kdefeq srcTy tgt then return e
  let tgtW ← whnf tgt
  let isOwn := match tgtW.getAppFn with | .const S _ => ownStruct env S | _ => false
  if tgtW.isForall || isOwn then
    return ← copyAt probe e tgtW path (fuel - 1)
  let ty := toString (← ppExpr tgt)
  modify (·.push (path ++ " : " ++ (if ty.length > 400 then (String.mk (ty.toList.take 400)) ++ "…" else ty))); return e

elab "kcopy " t:term : tactic => withMainContext do
  let g ← getMainGoal
  let tgt ← instantiateMVars (← g.getType)
  let e ← instantiateMVars (← Term.elabTermAndSynthesize t none)
  let (v, _) ← (copyAt false e tgt "" 64).run #[]
  g.assign (← instantiateMVars v)

elab "#kcopy_probe " t:term " : " ty:term : command => Command.runTermElabM fun _ => do
  let tgt ← instantiateMVars (← Term.elabType ty)
  let e ← instantiateMVars (← Term.elabTermAndSynthesize t none)
  let (_, bad) ← (copyAt true e tgt "" 64).run #[]
  logInfo m!"kcopy_probe: {bad.size} refused: {bad.toList}"

end Formalism.L2.Fam.KCopy


-- Positive and malicious negative controls, outside the pinned claimant file.
theorem direct_kcopy_true_control : True := by
  kcopy True.intro

theorem direct_kcopy_false_attack : False := by
  kcopy True.intro
