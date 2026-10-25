import DevelopmentalObservationBridge

/-!
Concrete finite dependency instantiation resembling V10 source-warrant cone.
This verifies only the logical effect of withdrawal for a stipulated graph.
It does NOT authenticate the historical Python source, its semantics,
the GitHub artifact, or a cross-language evidence bridge.
-/

namespace V10WarrantDependency

open DevelopmentalObservationBridge
open ScopedCertificates

inductive Node where
  | source
  | protectedDecision
  | independentNative
  deriving DecidableEq

def depends : Node → Node → Prop
  | .protectedDecision, .source => True
  | _, _ => False

def snapshot : AuthoritySnapshot Node where
  signed := fun _ => True
  permitted := fun _ => True
  denied := fun _ => False

theorem protected_reaches_source :
    Reaches depends .protectedDecision .source :=
  Reaches.direct (by trivial)

theorem protected_retracts_after_source_withdrawal :
    ¬ Valid (eligible (withdraw snapshot .source)) depends
      .protectedDecision := by
  exact withdraw_retracts_descendants snapshot depends
    .source .protectedDecision protected_reaches_source

theorem native_has_no_source_dependency :
    ∀ n, (n = .independentNative ∨
      Reaches depends .independentNative n) → n ≠ .source := by
  intro n h
  rcases h with hSelf | hPath
  · subst n
    decide
  · cases hPath with
    | direct h => simp [depends] at h
    | next h _ => simp [depends] at h

theorem native_previously_warranted :
    Valid (eligible snapshot) depends .independentNative := by
  apply Valid.admit
  · simp [eligible, snapshot]
  · intro parent h
    simp [depends] at h

theorem independent_native_survives_source_withdrawal :
    Valid (eligible (withdraw snapshot .source)) depends
      .independentNative := by
  exact independent_cone_survives snapshot depends
    .independentNative .source native_previously_warranted
    native_has_no_source_dependency

theorem no_release_without_external_permission :
    ¬ CanAct snapshot depends (fun _ : Unit => False)
      .protectedDecision () := by
  exact no_permission_escalation snapshot depends
    (fun _ : Unit => False) .protectedDecision () (by simp)

end V10WarrantDependency

#print axioms V10WarrantDependency.protected_retracts_after_source_withdrawal
#print axioms V10WarrantDependency.independent_native_survives_source_withdrawal
#print axioms V10WarrantDependency.no_release_without_external_permission
