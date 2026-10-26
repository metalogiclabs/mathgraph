"""Independent frozen-baseline regression, including native upstream replay in CI."""
import base64
import os
from pathlib import Path
import unittest

from paired_benchmark import (
    EDGE_TWO, EDGE_THREE, RIVALS, benchmark, cover_lookup,
    domain, minimum_separator, oracle, random_baseline,
    report_strategy, weighted_greedy, withheld_grammar_obstruction,
)


def synthetic_table(values):
    return {
        "reference": [oracle(x) for x in values],
        "standard_alphabet": [base64.b64encode(x).rstrip(b"=") for x in values],
        "unstripped_padding": [base64.urlsafe_b64encode(x) for x in values],
        "trailing_zero_loss": [
            base64.urlsafe_b64encode(x.rstrip(b"\x00") if len(x) % 3 == 0 else x).rstrip(b"=")
            for x in values
        ],
    }


class PairedBaselineTests(unittest.TestCase):
    def setUp(self):
        self.inputs = domain()
        self.table = synthetic_table(self.inputs)
        self.cover = cover_lookup(self.inputs, self.table)

    def test_same_domain_and_pool(self):
        self.assertEqual(len(self.inputs), 1026)
        self.assertEqual(len(set(self.inputs)), 1026)
        self.assertEqual(set(RIVALS), {"standard_alphabet", "trailing_zero_loss", "unstripped_padding"})

    def test_exact_minimum_and_conventional_greedy_tie(self):
        exact = minimum_separator(self.inputs, self.table)
        self.assertEqual(exact["status"], "MINIMUM_BASIS")
        self.assertEqual(exact["tests_hex"], ["00", "f80000"])
        self.assertEqual(exact["total_synthetic_cost"], 6)
        conventional = report_strategy(weighted_greedy(self.inputs, self.cover),self.cover)
        self.assertTrue(conventional["fully_separates_declared_pool"])
        self.assertEqual(conventional["synthetic_cost"], 6)
        self.assertEqual(conventional["tests"], 2)

    def test_edge_case_controls(self):
        simple = report_strategy(EDGE_TWO,self.cover)
        extended = report_strategy(EDGE_THREE,self.cover)
        self.assertEqual(simple["mutants_caught_count"], 2)
        self.assertFalse(simple["fully_separates_declared_pool"])
        self.assertEqual(extended["mutants_caught_count"], 3)
        self.assertTrue(extended["fully_separates_declared_pool"])
        self.assertEqual(simple["synthetic_cost"], 4)
        self.assertEqual(extended["synthetic_cost"], 8)

    def test_frozen_seeded_random(self):
        random_rows = random_baseline(self.inputs,self.cover)
        for size,count in [(2,19),(4,60),(8,151),(16,314)]:
            row = random_rows[str(size)]
            self.assertEqual(row["seeds"],1000)
            self.assertEqual(row["fully_separating_seeds"],count)

    def test_falsifying_counterexample_outside_grammar(self):
        result = withheld_grammar_obstruction(self.inputs,(b"\x00",b"\xf8\x00\x00"))
        self.assertFalse(result["caught_within_frozen_domain"])
        self.assertEqual(result["counterexample_hex"],"ffffffff")
        self.assertIn("OUTSIDE_DECLARED_GRAMMAR",result["disposition"])

    def test_native_pinned_source_only_when_available(self):
        checkout = os.environ.get("MATHGRAPH_PINNED_UPSTREAM")
        if not checkout:
            self.skipTest("needs separately pinned source checkout")
        output = benchmark(Path(checkout))
        self.assertEqual(output["source"]["commit"],
                         "672971d66a2ef9f85151e53283113f33d642dabd")
        self.assertEqual(set(output["original_upstream_test_receipts"]),
                         set(RIVALS)|{"reference"})
        self.assertTrue(all(x["status"]=="WARRANTED"
                       for x in output["original_upstream_test_receipts"].values()))
        self.assertTrue(output["exact_mathgraph"]["fully_separates_declared_pool"])
        self.assertEqual(output["informed_mutation_greedy"]["synthetic_cost"],6)


if __name__=="__main__": unittest.main()
