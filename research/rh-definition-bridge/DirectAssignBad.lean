import Lean

open Lean Elab Tactic Meta

-- Exact pinned source body of the custom `kexactB` tactic, reproduced with
-- only Lean imported.  It does NOT check the assigned expression against
-- the expected goal type before assigning the metavariable.
elab "kexactB " e:term : tactic => withMainContext do
  let g ← getMainGoal
  let v ← Term.elabTermAndSynthesize e none
  g.assign (← instantiateMVars v)

-- Deliberately malformed; source elaboration may accept the assignment,
-- but an honest kernel MUST reject the theorem declaration.
theorem direct_assign_false_attack : False := by
  kexactB True.intro
