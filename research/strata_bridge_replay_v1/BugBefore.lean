import Strata.Languages.Core
import StrataDDM.Integration.Lean.HashCommands
import Strata.MetaVerifier

open StrataDDM (Program)

namespace Strata

/-- This published counterexample is retrospective, originally reported in Strata #1488. -/
def divPgm : Program :=
#strata
program Core;
procedure P(x : bv W8) {
  assert [udiv_zero]: bv8.uDiv(x, bv{8}(0)) == bv{8}(0);
};
#end

/-- Step 1. The generated Lean goal incorrectly interprets division by zero. -/
theorem bogus : smtVCsCorrect divPgm := by
  gen_smt_vcs
  intro x
  exact BitVec.udiv_zero

/-- Independently stated finite concrete SMT query, equal to the source-generated VC. -/
def divVCs : SMT.SMTVCs :=
  let bv8 : SMT.TermType := .prim (.bitvec 8)
  let x : SMT.Term := .app (.uf ⟨"x@1", [], bv8⟩) [] bv8
  [("udiv_zero", { ufs := #[⟨"x@1", [], bv8⟩] }, [],
    .app .eq [.app .bvudiv [x, .prim (.bitvec 0#8)] bv8, .prim (.bitvec 0#8)] (.prim .bool))]

theorem divPgm_vcs : genSMTVCs divPgm = some divVCs := by
  native_decide

theorem real_meaning (h : smtVCsCorrect divPgm) : ∀ x : BitVec 8, x.smtUDiv 0#8 = 0#8 := by
  rw [smtVCsCorrect, divPgm_vcs] at h
  exact h

/-- Step 2: the actual denotation of the alleged certificate implies False. -/
theorem oops : False := by
  have h := real_meaning bogus 0#8
  rw [BitVec.smtUDiv_zero] at h
  exact absurd h (by decide)

#print axioms bogus
#print axioms oops
#check oops
end Strata