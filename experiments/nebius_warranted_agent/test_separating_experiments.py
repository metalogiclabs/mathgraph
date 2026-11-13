"""Independent finite audit including exhaustive two-test cost comparison."""
from itertools import combinations
import unittest
from separating_experiments import (
    BASE, DOMAIN, CAP10, GOOD, HYPOTHESES, candidate_expression,
    evaluate, oracle, case_cost, passing_hypotheses,
    separating_basis, generated_tests, run_demo,
)

class SeparatingExperimentTests(unittest.TestCase):
    def test_reference_contract(self):
        self.assertEqual(oracle((15,0,20)),15)
        self.assertEqual(oracle((-1,-2,5)),-1)
        self.assertEqual(oracle((30,2,12)),12)

    def test_interpreter_exposes_defect(self):
        expr=candidate_expression(CAP10)
        self.assertEqual(evaluate(expr,(15,0,20)),10)
        self.assertNotEqual(evaluate(expr,(15,0,20)),oracle((15,0,20)))

    def test_original_suite_passes_all_mutants(self):
        surviving=passing_hypotheses()
        self.assertEqual(set(surviving),set(HYPOTHESES))
        self.assertTrue(all(evaluate(surviving["cap10"],c)==oracle(c) for c in BASE))

    def test_basis_separates_all_rivals(self):
        surviving=passing_hypotheses()
        basis=separating_basis(surviving)
        self.assertEqual(basis["status"],"MINIMUM_BASIS")
        self.assertEqual(len(basis["tests"]),2)
        for name in ("cap10","cap11","floor0"):
            self.assertTrue(any(evaluate(surviving[name],tuple(c))!=oracle(tuple(c))
                                for c in basis["tests"]))
        self.assertEqual(basis["total_cost"],sum(case_cost(tuple(c)) for c in basis["tests"]))

    def test_independent_brute_force_minimum(self):
        surviving=passing_hypotheses()
        rivals=[surviving[n] for n in ("cap10","cap11","floor0")]
        usable=[]
        for c in DOMAIN:
            mask=sum(1<<i for i,x in enumerate(rivals) if evaluate(x,c)!=oracle(c))
            if mask:
                usable.append((c,mask))
        costs=[case_cost(c) for c,m in usable if m==7]
        costs += [case_cost(a)+case_cost(b) for (a,x),(b,y) in combinations(usable,2) if x|y==7]
        self.assertEqual(separating_basis(surviving)["total_cost"],min(costs))

    def test_obstruction_when_no_permitted_separators(self):
        basis=separating_basis(passing_hypotheses(),domain=BASE)
        self.assertEqual(basis["status"],"OBSTRUCTION")
        self.assertCountEqual(basis["unsplittable"],("cap10","cap11","floor0"))

    def test_no_rivals_costs_zero(self):
        basis=separating_basis({"correct":candidate_expression(GOOD)})
        self.assertEqual(basis["status"],"MINIMUM_BASIS")
        self.assertEqual(basis["tests"],[])
        self.assertEqual(basis["total_cost"],0)

    def test_no_unsafe_expression(self):
        examples=[
            "import os\n"+GOOD,
            'def clamp(value, minimum, maximum):\n return __import__("os")\n',
            "def clamp(value, minimum, maximum):\n return value + 2\n",
            "def clamp(value, minimum, maximum):\n return max(value, False)\n",
            "def clamp(value, minimum, maximum):\n return value.__class__\n",
            "def clamp(value, minimum, maximum):\n return min(value, 1000000000000)\n",
        ]
        for text in examples:
            with self.subTest(text=text), self.assertRaises(ValueError):
                candidate_expression(text)

    def test_generated_tests_take_results_from_independent_oracle(self):
        tests=generated_tests([(12,0,12),(-1,-2,5)])
        self.assertIn("clamp(12, 0, 12), 12",tests)
        self.assertIn("clamp(-1, -2, 5), -1",tests)

    def test_finite_domain_distinguishes_all_mutants(self):
        for name in ("cap10","cap11","floor0"):
            expr=candidate_expression(HYPOTHESES[name])
            self.assertTrue(any(evaluate(expr,c)!=oracle(c) for c in DOMAIN))
        expr=candidate_expression(GOOD)
        self.assertTrue(all(evaluate(expr,c)==oracle(c) for c in DOMAIN))

    def test_full_test_acquisition_and_receipt_withdrawal(self):
        result=run_demo()
        self.assertEqual(result["comparison"],{
            "fixed_test_only":"WARRANTED",
            "after_separating_test":"REJECTED",
            "after_scripted_repair":"WARRANTED",
            "finite_domain_checked":len(DOMAIN),
            "finite_domain_agreement":True})
        self.assertEqual([e["state"] for e in result["timeline"]],
                         ["WARRANTED","UNKNOWN","REJECTED","REJECTED","REJECTED","WARRANTED"])

if __name__=="__main__":
    unittest.main()
