import unittest
from mathgraph_check.finite_logic import compare_finite_formulas, UnsupportedFiniteGrammar

p = {"var": "p"}
q = {"var": "q"}


class FiniteLogicTest(unittest.TestCase):
    def test_demorgan_equivalence_is_scoped(self):
        left = {"not": {"and": [p, q]}}
        right = {"or": [{"not": p}, {"not": q}]}
        result = compare_finite_formulas(left, right, ["p", "q"])
        self.assertEqual(result["result"], "FINITE_MATCH_ON_DECLARED_DOMAIN")
        self.assertEqual(result["evaluated_assignments"], 4)
        self.assertEqual(result["contract_audit_status"], "SCOPED_AGREEMENT_SEMANTICS_UNKNOWN")
        self.assertFalse(result["epistemic"]["truth_promotion"])
        self.assertEqual(result["epistemic"]["verified_badge"], "NOT_ISSUED")

    def test_unexpectedly_strong_antecedent_has_counterexample(self):
        left = {"implies": [{"and": [p, {"not": p}]}, q]}
        right = {"implies": [p, q]}
        result = compare_finite_formulas(left, right, ["p", "q"])
        self.assertEqual(result["result"], "FINITE_COUNTEREXAMPLE")
        self.assertEqual(result["witness"]["assignment"], {"p": True, "q": False})
        self.assertEqual(result["witness"]["source"], True)
        self.assertEqual(result["witness"]["formal"], False)
        self.assertEqual(result["contract_audit_status"], "DIVERGENT_PROTECTED_CONTRACT")

    def test_vacuity_equivalence_is_not_intent_fidelity(self):
        left = {"implies": [{"and": [p, {"not": p}]}, q]}
        right = {"const": True}
        r = compare_finite_formulas(left, right, ["p", "q"])
        self.assertEqual(r["result"], "FINITE_MATCH_ON_DECLARED_DOMAIN")
        self.assertEqual(r["epistemic"]["natural_language_fidelity"], "UNKNOWN")

    def test_unsupported_formal_domain_returns_unknown(self):
        r = compare_finite_formulas({"forallNat": p}, p, ["p"])
        self.assertEqual(r["result"], "UNKNOWN_UNSUPPORTED_GRAMMAR")
        self.assertEqual(r["epistemic"]["verified_badge"], "NOT_ISSUED")

    def test_malformed_term_is_not_silently_accepted(self):
        for expr in [{"const": 1}, {"var": "z"}, {"and": [p]},
                     {"const": True, "var": "p"}]:
            with self.subTest(expr=expr):
                r = compare_finite_formulas(expr, p, ["p"])
                self.assertEqual(r["result"], "UNKNOWN_UNSUPPORTED_GRAMMAR")

    def test_rejects_invalid_variable_scope(self):
        for v in [[], ["p", "p"], ["x"] * 6, ["!bad"]]:
            with self.subTest(v=v):
                with self.assertRaises(UnsupportedFiniteGrammar):
                    compare_finite_formulas(p, p, v)

    def test_same_surface_different_meaning_is_not_merged(self):
        r = compare_finite_formulas({"const": True}, {"const": False}, ["p"])
        self.assertEqual(r["result"], "FINITE_COUNTEREXAMPLE")

    def test_xor_and_iff_witnesses(self):
        r = compare_finite_formulas({"xor": [p, q]}, {"iff": [p, q]}, ["p", "q"])
        self.assertEqual(r["result"], "FINITE_COUNTEREXAMPLE")
        self.assertEqual(r["witness"]["assignment"], {"p": False, "q": False})

    def test_complexity_budget_returns_unknown(self):
        expr = p
        for _ in range(30):
            expr = {"not": expr}
        r = compare_finite_formulas(expr, p, ["p"])
        self.assertEqual(r["result"], "UNKNOWN_UNSUPPORTED_GRAMMAR")


if __name__ == "__main__":
    unittest.main()
