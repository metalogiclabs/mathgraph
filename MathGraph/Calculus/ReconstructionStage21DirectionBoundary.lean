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

/-- The opposite source gives the mirror residual as well: identity reaches
`true`, while the empty raw generator cannot continue from `true` to `false`. -/
theorem stage21_cold_true_generic_residual :
    ProbeResidual Stage13G0 (NoProbes Bool) true true false := by
  refine ⟨noProbes_consequentialEq true false, ?_⟩
  intro hEq
  have hTrue : ProbeObservation Stage13G0 true true :=
    ⟨(.nil : FreePath Stage13G0 true true)⟩
  have hFalse : ProbeObservation Stage13G0 true false := hEq.mp hTrue
  rcases hFalse with ⟨p⟩
  cases p with
  | step e _rest =>
      exact e.elim

/-- The Stage-20 rule therefore admits raw generator evidence in both endpoint
directions. This is the sharper result exposed by the first Stage-21 attempt:
the symmetric cold residual does not fail to orient; rather, distinct source
witnesses symmetrically license both orientations. -/
theorem stage21_cold_stage20_generates_both_directions :
    Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
    Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false) := by
  constructor
  · refine ⟨⟨false, ?_⟩⟩
    exact ⟨stage19_cold_generic_residual,
      ⟨(.nil : FreePath Stage13G0 false false)⟩⟩
  · refine ⟨⟨true, ?_⟩⟩
    exact ⟨stage21_cold_true_generic_residual,
      ⟨(.nil : FreePath Stage13G0 true true)⟩⟩

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

The Stage-6 residual survives endpoint reversal. In the symmetric cold world,
Stage 20 can also realize both directed raw edges, using the corresponding
endpoint as the positive source witness. But no chooser on the unordered
Bool pair can simultaneously ignore endpoint presentation order and commute
with the carrier's nontrivial renaming.

Thus bare residual differentiation does not canonically select a unique
direction. Any unique directed genesis must obtain symmetry-breaking evidence
from somewhere else (for example a distinguished source, goal, intervention,
resource gradient, temporal order, or other oriented structure). -/
theorem reconstruction_stage21_direction_boundary_certificate :
    (ProbeResidual Stage13G0 (NoProbes Bool) false false true ∧
     ProbeResidual Stage13G0 (NoProbes Bool) false true false) ∧
    (Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) false true) ∧
     Nonempty (Stage20Generator Stage13G0 (NoProbes Bool) true false)) ∧
    (¬ Nonempty Stage21CanonicalOrientation) := by
  exact ⟨stage21_cold_residual_has_both_presentations,
    stage21_cold_stage20_generates_both_directions,
    stage21_no_canonical_orientation_from_symmetric_pair⟩

end MathGraph.Calculus
