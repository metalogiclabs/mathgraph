import SymbolResourceBridge

/-! Exact coin-distribution preservation for a finite-symbol source machine
and its compiled pinned OAI Boolean-track implementation. -/

namespace Metalogic.OpenAIMath.SymbolProbabilityBridge

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.SymbolMachineBridge
open Metalogic.OpenAIMath.SymbolRunBridge
open Metalogic.OpenAIMath.SymbolResourceBridge

variable {α : Type} [DecidableEq α] {K q w h : ℕ}

/-- Acceptance probability under exactly the same uniform finite coin-prefix
measure as OpenAI's target definition, evaluated on the source machine. -/
def sourceAcceptanceProbability (M : SymbolMachine α q w h) (blank : α)
    (x : Word) (t : ℕ) : ℚ :=
  ((Finset.univ.filter (fun bits : Fin t → Bool =>
    M.output (sourceRun M blank x (Machine.extendCoins bits) t).state =
      some true)).card : ℚ) / (2 : ℚ) ^ t

/-- The independently verified whole-run compiler preserves acceptance
probability at EVERY finite clock, not just final decision outcomes. -/
theorem compiled_acceptanceProbability_eq_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (x : Word) (t : ℕ) :
    (compileMachine codec M).acceptanceProbability x t =
      sourceAcceptanceProbability M codec.blank x t := by
  have hfilter :
      (Finset.univ.filter (fun bits : Fin t → Bool =>
        (compileMachine codec M).output
          ((compileMachine codec M).run x (Machine.extendCoins bits) t).state =
            some true)) =
      (Finset.univ.filter (fun bits : Fin t → Bool =>
        M.output (sourceRun M codec.blank x (Machine.extendCoins bits) t).state =
          some true)) := by
    ext bits
    simp only [Finset.mem_filter, Finset.mem_univ, true_and]
    rw [compiled_output_eq_source codec M x (Machine.extendCoins bits) t]
  unfold Machine.acceptanceProbability sourceAcceptanceProbability
  rw [hfilter]

/-- The source's determinism, logarithmic-space bound, and total decision
contract compile to a polynomially clocked OAI machine. The final complexity
step uses OpenAI's already verified pinned clock theorem; it is not an
independent reconstruction of that upstream clock lemma. -/
theorem compiled_polynomial_clock_of_source
    (codec : AlphabetCodec α K) (M : SymbolMachine α q w h)
    (hdet : ∀ st inp bits,
      M.transition st inp bits false = M.transition st inp bits true)
    (hs : SourceLogSpace M codec.blank)
    (A : Language) (hdec : SourceDecides M codec.blank A) :
    ∃ c k : ℕ, 0 < c ∧ ∀ x : Word,
      (compileMachine codec M).HaltsBy x (polynomialClock c k x.length) := by
  exact (compiled_deterministic_of_source codec M hdet).polynomial_clock
    (compiled_LogSpace_of_source codec M hs)
    (compiled_decides_of_source codec M A hdec)

end Metalogic.OpenAIMath.SymbolProbabilityBridge
