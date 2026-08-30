import MathGraph.Calculus.ReconstructionStage14ConstructorGenesis

namespace MathGraph.Calculus

/-- Stage 15 moves from a one-shot language extension to a recursively updated
 developmental state. The world, current probe interface, and available
 constructor language are now carried together. -/
inductive Stage15World where
  | cold
  | warm
  deriving DecidableEq

/-- The world component compiles back to the same raw generator semantics used
 throughout the reconstruction. -/
def Stage15Generator : Stage15World → Bool → Bool → Type
  | .cold => Stage13G0
  | .warm => oneEdgeGenerator

structure Stage15State where
  world : Stage15World
  probes : List Bool
  language : List Stage14Constructor
  deriving DecidableEq

noncomputable local instance stage15ResidualPropDecidable (p : Prop) : Decidable p :=
  Classical.propDecidable p

/-- Residual selection is now a function of the current developmental state. -/
noncomputable def Stage15Select (s : Stage15State) : List Bool :=
  finiteResidualSelect (Stage15Generator s.world) Stage13Candidates s.probes

/-- Only probes newly introduced by this cycle count as the residual delta. -/
def Stage15NewProbes (s : Stage15State) (selected : List Bool) : List Bool :=
  selected.filter (fun p => p ∉ s.probes)

/-- The same Stage-14 compilation law turns a newly selected `false` source
 into the constructor-language delta. Other residuals may refine observation
 without silently inventing an unrelated constructor. -/
def Stage15ConstructorDelta (newProbes : List Bool) : List Stage14Constructor :=
  Stage14ConstructorExtension newProbes

/-- Installing `cross` changes the raw world; otherwise the prior world is
 preserved. -/
def Stage15NextWorld (w : Stage15World)
    (delta : List Stage14Constructor) : Stage15World :=
  if .cross ∈ delta then .warm else w

/-- One recursive developmental step. Exactly the same state-to-residual-to-
 delta law can be applied again to its own output. -/
noncomputable def Stage15Step (s : Stage15State) : Stage15State :=
  let selected := Stage15Select s
  let newProbes := Stage15NewProbes s selected
  let delta := Stage15ConstructorDelta newProbes
  { world := Stage15NextWorld s.world delta
    probes := selected
    language := delta ++ s.language }

/-- Initial state: cold world, no observations, and only the idle constructor. -/
def Stage15S0 : Stage15State :=
  { world := .cold, probes := [], language := Stage14K0 }

/-- First successor: the old residual creates the cross constructor and warms
 the world while retaining the selected source as part of state. -/
def Stage15S1 : Stage15State :=
  { world := .warm, probes := [false], language := [.cross, .idle] }

/-- The newly warmed world creates a genuinely new residual: source `true`
 reaches `true` but cannot reach `false`, while the retained `false` probe
 reaches both endpoints and therefore does not distinguish them. -/
theorem stage15_warm_true_residual_after_promotion :
    ListProbeResidual oneEdgeGenerator [false] true := by
  refine ⟨false, true, ?_, ?_⟩
  · intro k hk
    have hkFalse : k = false := by simpa using hk
    subst k
    apply propext
    constructor
    · intro _
      exact ⟨oneEdge_false_to_true⟩
    · intro _
      exact ⟨(.nil : FreePath oneEdgeGenerator false false)⟩
  · intro hEq
    have hTrue : ProbeObservation oneEdgeGenerator true true :=
      ⟨(.nil : FreePath oneEdgeGenerator true true)⟩
    have hBad : ProbeObservation oneEdgeGenerator true false := hEq.mpr hTrue
    rcases hBad with ⟨p⟩
    exact (oneEdge_no_reverse p).elim

/-- The already-retained source is redundant in the warmed state. -/
theorem stage15_warm_false_redundant :
    ListProbeRedundant oneEdgeGenerator [false] false :=
  member_listProbeRedundant (by simp)

/-- Therefore applying the same finite selector to the first successor selects
 exactly the newly exposed `true` source. -/
theorem stage15_second_selection :
    finiteResidualSelect oneEdgeGenerator Stage13Candidates [false] =
      [true, false] := by
  have hFalseNo : ¬ ListProbeResidual oneEdgeGenerator [false] false :=
    (noListProbeResidual_iff_redundant oneEdgeGenerator [false] false).mpr
      stage15_warm_false_redundant
  change
    (if ListProbeResidual oneEdgeGenerator [false] false then
       finiteResidualSelect oneEdgeGenerator [true] [false, false]
     else finiteResidualSelect oneEdgeGenerator [true] [false]) = [true, false]
  rw [if_neg hFalseNo]
  change
    (if ListProbeResidual oneEdgeGenerator [false] true then
       finiteResidualSelect oneEdgeGenerator [] [true, false]
     else finiteResidualSelect oneEdgeGenerator [] [false]) = [true, false]
  rw [if_pos stage15_warm_true_residual_after_promotion]
  rfl

/-- Second successor: the same recursive law reacts to the residual created by
 its own prior promotion. No new constructor is licensed, but the observational
 interface develops again. -/
def Stage15S2 : Stage15State :=
  { world := .warm, probes := [true, false], language := [.cross, .idle] }

/-- The first application of the recursive operator reproduces Stage 14's
 constructor-language/world transition as an actual state transition. -/
theorem stage15_first_step : Stage15Step Stage15S0 = Stage15S1 := by
  simp [Stage15Step, Stage15S0, Stage15S1, Stage15Select,
    Stage15Generator, stage13_selection_is_endogenous, Stage15NewProbes,
    Stage15ConstructorDelta, Stage14ConstructorExtension, Stage15NextWorld,
    Stage14K0]

/-- Applying that same operator to its own output consumes the new residual
 caused by the changed closure and reaches the second successor. -/
theorem stage15_second_step : Stage15Step Stage15S1 = Stage15S2 := by
  simp [Stage15Step, Stage15S1, Stage15S2, Stage15Select,
    Stage15Generator, stage15_second_selection, Stage15NewProbes,
    Stage15ConstructorDelta, Stage14ConstructorExtension, Stage15NextWorld]

/-- Once both possible source probes are retained, every candidate is already
 redundant, so the finite selector is at a fixed point. -/
theorem stage15_saturated_selection :
    finiteResidualSelect oneEdgeGenerator Stage13Candidates [true, false] =
      [true, false] := by
  apply finiteResidualSelect_no_residual_no_extension
  intro k hk
  apply member_listProbeRedundant
  cases k <;> simp

/-- The recursive developmental state itself reaches a fixed point under the
 same update law rather than requiring an external stop instruction. -/
theorem stage15_fixed_point : Stage15Step Stage15S2 = Stage15S2 := by
  simp [Stage15Step, Stage15S2, Stage15Select, Stage15Generator,
    stage15_saturated_selection, Stage15NewProbes,
    Stage15ConstructorDelta, Stage14ConstructorExtension, Stage15NextWorld]

/-- Exact first-delta ablation recovers the original cold inability to reach
 the target. -/
theorem stage15_first_delta_ablation_restores_failure :
    ¬ Nonempty (FreePath (Stage15Generator Stage15S0.world) false true) := by
  exact stage13_cold_target_unreachable

/-- The first recursive successor changes reachable closure. -/
theorem stage15_first_successor_reaches_target :
    Nonempty (FreePath (Stage15Generator Stage15S1.world) false true) := by
  exact ⟨oneEdge_false_to_true⟩

/-- Stage-15 recursive-development certificate.

A single state transformer is now reapplied to its own outputs:
* S0 --step--> S1 because a residual expands the constructor language and raw
  reachable closure;
* that changed closure itself exposes a new residual;
* S1 --step--> S2 by the same law, refining the retained observational state;
* S2 is a verified fixed point because all finite source candidates are then
  redundant;
* ablating the first constructor delta restores the original reachability
  obstruction.

This is a finite self-application result. The meta-level datatype containing
 the possible constructor *kinds* is still fixed; full constructor-kind genesis
 remains a deeper boundary. -/
theorem reconstruction_stage15_recursive_development_certificate :
    Stage15Step Stage15S0 = Stage15S1 ∧
    Stage15Step Stage15S1 = Stage15S2 ∧
    Stage15Step Stage15S2 = Stage15S2 ∧
    (¬ Nonempty (FreePath (Stage15Generator Stage15S0.world) false true)) ∧
    Nonempty (FreePath (Stage15Generator Stage15S1.world) false true) :=
  ⟨stage15_first_step,
   stage15_second_step,
   stage15_fixed_point,
   stage15_first_delta_ablation_restores_failure,
   stage15_first_successor_reaches_target⟩

end MathGraph.Calculus
