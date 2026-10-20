/- Control, unchanged across exposed main and proposed repair. -/
import Strata.Languages.Core
import StrataDDM.Integration.Lean.HashCommands
import Strata.MetaVerifier

open StrataDDM (Program)

namespace Strata

private def minPgm : Program :=
#strata
program Core;
procedure min(n : int, m : int, out k : int)
spec {
  ensures (int.le(k, n) && int.le(k, m));
}
{
  k := if int.lt(n, m) then n else m;
  k := k;
};
#end

theorem minCorrect : smtVCsCorrect minPgm := by
  gen_smt_vcs
  grind

-- Independent built-in semantic oracle: Lean's unsigned BitVec division
-- returns 0 at divisor zero; SMT-LIB's smtUDiv returns all ones.
theorem plain_div_zero : ((0#8 : BitVec 8) / 0#8) = 0#8 := by decide
theorem smt_div_zero : (0#8 : BitVec 8).smtUDiv 0#8 = 255#8 := by decide
#print axioms minCorrect
#print axioms plain_div_zero
#print axioms smt_div_zero
#eval "MATHGRAPH_CONTROL_GREEN"
end Strata
