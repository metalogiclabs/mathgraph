import VerifiedDevelopmentalNavigation

namespace VerifiedDevelopmentalNavigation

/-!
# Certified developmental phase change

This is the smallest evidence object that licenses the strong claim that a
verified action-language extension produced a genuine capability phase change
inside a declared boundary while preserving all old capability.
-/

/-- A bounded capability phase-change certificate packages:

1. an explicit old-world trace boundary,
2. a finite complete cover of that boundary,
3. verified failure of every covered old trace,
4. a conservative embedding of the old action language into the new one, and
5. a verified new-world witness reaching the protected target.

The certificate deliberately makes no claim outside its declared old boundary.
-/
structure CapabilityPhaseChangeCertificate
    {X C O A₀ A₁ : Type}
    (W₀ : World X C A₀ O) (W₁ : World X C A₁ O)
    (start target : X) where
  boundary : World.TraceBoundary (A := A₀)
  cover : List (List A₀)
  complete : World.CompleteCover boundary cover
  blocked : ∀ trace ∈ cover, W₀.run trace start ≠ some target
  extension : ActionExtension W₀ W₁
  witness : W₁.Reachable start target

namespace CapabilityPhaseChangeCertificate

variable {X C O A₀ A₁ : Type}
variable {W₀ : World X C A₀ O} {W₁ : World X C A₁ O}
variable {start target : X}

/-- The old target is certified unreachable inside the declared boundary. -/
theorem old_unreachable_within
    (cert : CapabilityPhaseChangeCertificate W₀ W₁ start target) :
    ¬ W₀.ReachableWithin cert.boundary start target := by
  exact W₀.unreachableWithin_of_completeCover
    cert.boundary cert.cover start target cert.complete cert.blocked

/-- The extension reaches the protected target. -/
theorem new_reachable
    (cert : CapabilityPhaseChangeCertificate W₀ W₁ start target) :
    W₁.Reachable start target :=
  cert.witness

/-- The certified phase-change statement: bounded old-world impossibility plus
new-world verified reachability. -/
theorem phase_change
    (cert : CapabilityPhaseChangeCertificate W₀ W₁ start target) :
    (¬ W₀.ReachableWithin cert.boundary start target) ∧
      W₁.Reachable start target := by
  exact ⟨cert.old_unreachable_within, cert.witness⟩

/-- Development is conservative: every capability already reachable in the old
world remains reachable after the certified extension. -/
theorem retains_old_capability
    (cert : CapabilityPhaseChangeCertificate W₀ W₁ start target)
    {x y : X} (h : W₀.Reachable x y) : W₁.Reachable x y := by
  exact cert.extension.reachability_monotone h

end CapabilityPhaseChangeCertificate

end VerifiedDevelopmentalNavigation
