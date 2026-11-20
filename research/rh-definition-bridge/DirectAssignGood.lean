import Lean

open Lean Elab Tactic Meta

-- Exact pinned source body of the custom `kexactB` tactic, reproduced with
-- only Lean imported.  It does NOT check the assigned expression against
-- the expected goal type before assigning the metavariable.
elab "kexactB " e:term : tactic => withMainContext do
  let g ← getMainGoal
  let v ← Term.elabTermAndSynthesize e none
  g.assign (← instantiateMVars v)

theorem direct_assign_true_control : True := by
  kexactB True.intro
