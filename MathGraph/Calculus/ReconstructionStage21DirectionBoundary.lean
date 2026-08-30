import MathGraph.Calculus.ReconstructionStage20ResidualClosure

namespace MathGraph.Calculus

/-- The generic residual reconstructed at Stage 6 is intrinsically symmetric in
its endpoint pair. It records that the old language identifies the endpoints
and the new observation separates them; neither fact chooses a direction. -/
theorem probeResidual_symm
    {ι Ω : Type} {G : Ω → Ω → Type} {P : ProbeFamily ι Ω}
    {k x y : Ω}
    (r : ProbeResidual G P k x y) :
    ProbeResidual G P k y x := by
  refine ⟨consequentialEq_symm r.indistinguishable, ?_⟩
  intro h
  exact r.separated h.symm

/-- In the cold Bool world exactly the same generic residual is available under
both presentations of the endpoint pair. -/
theorem stage21_cold_residual_has_both_presentations :
    ProbeResidual Stage13G0 (NoProbes Bool) false false true ∧
    ProbeResidual Stage13G0 (NoProbes Bool) false true false := by
  constructor
  · exact stage19_cold_generic_residual
  · exact probeResidual_symm stage19_cold_generic_residual

/-- Yet the reverse directed generator is absent. Stage 20 succeeds only in the
orientation whose left endpoint has a positive reachability witness. Thus the
bare symmetric residual does not itself determine the directed edge. -/
theorem stage21_reverse_residual_without_orientation_has_no_generator :
    ProbeResidual Stage13G0 (NoProbes Bool) false true false ∧
    ¬ Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false) := by
  constructor
  · exact probeResidual_symm stage19_cold_generic_residual
  · intro h
    rcases h with ⟨e⟩
    exact stage13_cold_target_unreachable e.property.2

/-- A genuinely canonical orientation extracted from an unordered symmetric
residual should not depend on whether its two endpoints were presented as
`x,y` or `y,x`, and it should commute with a renaming of the state carrier.
For Bool, the nontrivial renaming is negation. -/
structure Stage21CanonicalOrientation where
  choose : Bool → Bool → Bool
  swap_invariant : ∀ x y, choose x y = choose y x
  rename_equivariant : ∀ x y,
    choose (Bool.not x) (Bool.not y) = Bool.not (choose x y)

/-- There is no endpoint orientation satisfying both presentation symmetry and
state-renaming equivariance on the two-point carrier. The obstruction is
structural: swapping `false,true` is exactly the same transformation as the
nontrivial state renaming, so any purported canonical choice would have to be
fixed by Bool negation. -/
theorem stage21_no_canonical_orientation_from_symmetric_pair :
    ¬ Nonempty Stage21CanonicalOrientation := by
  intro h
  rcases h with ⟨o⟩
  have hSwap : o.choose false true = o.choose true false :=
    o.swap_invariant false true
  have hRename : o.choose true false = Bool.not (o.choose false true) := by
    simpa using o.rename_equivariant false true
  have hFixed : o.choose false true = Bool.not (o.choose false true) :=
    hSwap.trans hRename
  cases hChoice : o.choose false true <;> simp [hChoice] at hFixed

/-- Stage-21 boundary certificate.

The Stage-6 residual survives endpoint reversal, while Stage-20 directed raw
edge evidence does not survive reversal without the positive reachability
orientation. Moreover no orientation of an unordered two-point residual can
respect both endpoint-swap invariance and state-renaming equivariance.

Therefore some symmetry-breaking directional evidence is necessary for
canonical directed generator genesis. In the current reconstruction that role
is played by positive reachability of the chosen source to one endpoint. -/
theorem reconstruction_stage21_direction_boundary_certificate :
    (ProbeResidual Stage13G0 (NoProbes Bool) false false true ∧
     ProbeResidual Stage13G0 (NoProbes Bool) false true false) ∧
    (¬ Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
    (¬ Nonempty Stage21CanonicalOrientation) := by
  refine ⟨stage21_cold_residual_has_both_presentations, ?_,
    stage21_no_canonical_orientation_from_symmetric_pair⟩
  exact stage21_reverse_residual_without_orientation_has_no_generator.2

end MathGraph.Calculus
