import MathGraph.Calculus.ReconstructionStage13Development

namespace MathGraph.Calculus

/-- Stage 14 makes the constructor language itself explicit. `idle` preserves
the cold generator; `cross` is the only constructor capable of installing the
new cross-endpoint possibility. -/
inductive Stage14Constructor where
  | idle
  | cross
  deriving DecidableEq

/-- A constructor compiles to a raw generator. Identity and composition are
still generated only by `FreePath`. -/
def Stage14Compile : Stage14Constructor → Bool → Bool → Type
  | .idle => Stage13G0
  | .cross => oneEdgeGenerator

/-- A constructor language is just the finite set of constructors currently
licensed for generation. -/
def Stage14CanForm (K : List Stage14Constructor)
    (c : Stage14Constructor) : Prop := c ∈ K

/-- The cold language contains no constructor that can install a cross edge. -/
def Stage14K0 : List Stage14Constructor := [.idle]

/-- The Stage-13 residual-selected source compiles into the minimum language
extension that licenses the missing constructor. This is intentionally a tiny
finite precursor to full self-hosting: the constructor *class* is still fixed,
but its available language is now part of developmental state. -/
def Stage14ConstructorExtension (selected : List Bool) :
    List Stage14Constructor :=
  if false ∈ selected then [.cross] else []

/-- Development extends the current constructor language by exactly the
residual-licensed constructor extension. -/
def Stage14DevelopLanguage (K : List Stage14Constructor)
    (selected : List Bool) : List Stage14Constructor :=
  Stage14ConstructorExtension selected ++ K

/-- The missing cross constructor is not formable in the cold language. -/
theorem stage14_cross_not_formable_cold :
    ¬ Stage14CanForm Stage14K0 .cross := by
  simp [Stage14CanForm, Stage14K0]

/-- Every constructor formable in the cold language compiles to the cold raw
world, so no cold-language term can reach the target. -/
theorem stage14_cold_language_cannot_generate_target :
    ∀ c, Stage14CanForm Stage14K0 c →
      ¬ Nonempty (FreePath (Stage14Compile c) false true) := by
  intro c hc
  have hcIdle : c = .idle := by
    simpa [Stage14CanForm, Stage14K0] using hc
  subst c
  exact stage13_cold_target_unreachable

/-- The verified Stage-13 residual selection forces exactly the cross
constructor extension. -/
theorem stage14_residual_forces_constructor_extension :
    Stage14ConstructorExtension
      (finiteResidualSelect Stage13G0 Stage13Candidates []) = [.cross] := by
  rw [stage13_selection_is_endogenous]
  simp [Stage14ConstructorExtension]

/-- After language development, the formerly unavailable constructor is
formable. -/
theorem stage14_cross_formable_after_development :
    Stage14CanForm
      (Stage14DevelopLanguage Stage14K0
        (finiteResidualSelect Stage13G0 Stage13Candidates []))
      .cross := by
  rw [stage13_selection_is_endogenous]
  simp [Stage14CanForm, Stage14DevelopLanguage, Stage14ConstructorExtension,
    Stage14K0]

/-- Compiling the newly formable constructor changes reachable closure: the
previously unreachable target now has a free path. -/
theorem stage14_warm_language_generates_target :
    Nonempty (FreePath (Stage14Compile .cross) false true) := by
  exact ⟨oneEdge_false_to_true⟩

/-- Exact constructor-language ablation restores non-formability and therefore
the cold reachability obstruction. -/
theorem stage14_exact_constructor_ablation_restores_failure :
    (¬ Stage14CanForm Stage14K0 .cross) ∧
    (¬ Nonempty (FreePath Stage13G0 false true)) :=
  ⟨stage14_cross_not_formable_cold, stage13_cold_target_unreachable⟩

/-- Negative law: without selection of the residual-bearing source, the
constructor-language extension is empty. -/
theorem stage14_no_selected_residual_no_constructor_extension
    (selected : List Bool) (h : false ∉ selected) :
    Stage14ConstructorExtension selected = [] := by
  simp [Stage14ConstructorExtension, h]

/-- Stage-14 constructor-language genesis certificate.

The developmental state now includes an available constructor language:
* K0 cannot even form the constructor needed for the target;
* the already verified residual selector determines a nonempty language delta;
* K1 = delta ++ K0 makes the missing constructor formable;
* compiling that constructor changes raw reachable closure;
* exact deletion of the language delta restores both non-formability and the
  original reachability failure;
* no selected residual yields no constructor extension.

This verifies developmental expansion of an available constructor language.
It does not yet claim ex-nihilo invention of a constructor outside the fixed
Stage14 constructor class; that is the next self-hosting boundary. -/
theorem reconstruction_stage14_constructor_genesis_certificate :
    (¬ Stage14CanForm Stage14K0 .cross) ∧
    (Stage14ConstructorExtension
      (finiteResidualSelect Stage13G0 Stage13Candidates []) = [.cross]) ∧
    Stage14CanForm
      (Stage14DevelopLanguage Stage14K0
        (finiteResidualSelect Stage13G0 Stage13Candidates []))
      .cross ∧
    Nonempty (FreePath (Stage14Compile .cross) false true) ∧
    (¬ Nonempty (FreePath Stage13G0 false true)) :=
  ⟨stage14_cross_not_formable_cold,
   stage14_residual_forces_constructor_extension,
   stage14_cross_formable_after_development,
   stage14_warm_language_generates_target,
   stage13_cold_target_unreachable⟩

end MathGraph.Calculus
