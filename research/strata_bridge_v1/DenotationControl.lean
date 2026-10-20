import Strata.MetaVerifier

-- Independent fixed-width arithmetic witness; no locally introduced bridge.
namespace MathGraphStrataOracle

theorem lean_bitvec_div_by_zero :
    ((0#8 : BitVec 8) / 0#8) = 0#8 := by decide

theorem smt_bitvec_div_by_zero :
    BitVec.smtUDiv (0#8 : BitVec 8) 0#8 = 255#8 := by decide

theorem division_semantics_differ :
    (BitVec.smtUDiv (0#8 : BitVec 8) 0#8) ≠
      ((0#8 : BitVec 8) / 0#8) := by decide

#print axioms lean_bitvec_div_by_zero
#print axioms smt_bitvec_div_by_zero
#print axioms division_semantics_differ
#eval ("MATHGRAPH_LEAN_DIV0=" ++ toString (((0#8 : BitVec 8) / 0#8).toNat))
#eval ("MATHGRAPH_SMT_DIV0=" ++ toString ((BitVec.smtUDiv (0#8 : BitVec 8) 0#8).toNat))
#eval "MATHGRAPH_STRATA_DENOTATION_ORACLE_PASSED"

end MathGraphStrataOracle
