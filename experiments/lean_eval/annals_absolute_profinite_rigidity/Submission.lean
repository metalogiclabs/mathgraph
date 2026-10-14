import ChallengeDeps

open AbsoluteProfiniteRigidity
open Group Polynomial

universe u
set_option autoImplicit false

/-- Zero-history separator probe: unfold only the benchmark predicate and ask
Mathlib for the structural instances before attempting the rigidity argument. -/
theorem theorem_7_1 : ProfinitelyRigid (BianchiGroup 3) := by
  unfold ProfinitelyRigid
  constructor
  · infer_instance
  constructor
  · infer_instance
  intro Λ _ _ hcomp
  aesop
