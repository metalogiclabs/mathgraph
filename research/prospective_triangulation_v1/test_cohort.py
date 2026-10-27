"""Contract-first tests for a frozen, source-authored finite migration cohort."""
import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def subject():
    try:
        return importlib.import_module("cohort")
    except ModuleNotFoundError as exc:
        raise AssertionError("prospective cohort implementation is absent") from exc


class SourceContractTests(unittest.TestCase):
    def test_unchanged_full_population_is_exactly_the_preregistered_1189(self):
        cohort = subject()
        cases = cohort.full_population()
        counts = {name: len(rows) for name, rows in cases.items()}
        self.assertEqual(counts, {
            "conditional_reset": 9,
            "vector_addition": 820,
            "search_replace": 360,
        })

    def test_source_outputs_preserve_separate_inputs_and_frame(self):
        cohort = subject()
        self.assertEqual(cohort.contract_output("conditional_reset", (3, 0)), (3, 0))
        self.assertEqual(cohort.contract_output("conditional_reset", (3, -1)), (0, -1))
        self.assertEqual(cohort.contract_output("vector_addition",
                                                (2, -1, 0, 0, 1, -1, 0)),
                         (0, -1, 0, 1, -1, 0))
        self.assertEqual(cohort.contract_output("search_replace",
                                                (3, -1, 1, -1, -1, 0)),
                         (0, 1, 0))

    def test_each_registered_mutant_has_a_real_separating_input(self):
        cohort = subject()
        expected = {
            "conditional_reset": {"always_zero", "never_zero"},
            "vector_addition": {"skip_last", "mutate_b"},
            "search_replace": {"skip_last", "replace_unequal"},
        }
        for case, names in expected.items():
            self.assertEqual(set(cohort.mutants(case)), names)
            for mutant in names:
                witnesses = [row for row in cohort.full_population()[case]
                             if cohort.mutant_output(case, mutant, row)
                             != cohort.contract_output(case, row)]
                self.assertTrue(witnesses, (case, mutant))

    def test_compiler_finds_two_decisive_reset_probes_and_independent_oracle_agrees(self):
        cohort = subject()
        result = cohort.synthesize_minimum_probes("conditional_reset")
        self.assertEqual(result["status"], "DECISION_SUFFICIENT_BASIS")
        self.assertEqual(result["basis_cost"], 2)
        self.assertEqual(result["conventional_minimum_cost"], 2)
        self.assertEqual(result["relative_result"], "BASELINE_TIE")

    def test_real_observation_cannot_be_warranted_without_pins_and_receipts(self):
        cohort = subject()
        contract = cohort.contract_output("conditional_reset", (3, 1))
        evidence = {"source_pin_ok": True, "target_pin_ok": True,
                    "native_source": contract, "native_target": contract,
                    "contract_active": True}
        self.assertEqual(cohort.review_one("conditional_reset", (3, 1), evidence),
                         "WARRANTED_BOUNDED_MATCH")
        for key in ("source_pin_ok", "target_pin_ok", "contract_active"):
            invalid = dict(evidence, **{key: False})
            self.assertEqual(cohort.review_one("conditional_reset", (3, 1), invalid),
                             "UNKNOWN_SOURCE_AUTHORITY")
        self.assertEqual(cohort.review_one("conditional_reset", (3, 1),
                                          dict(evidence, native_target=None)),
                         "UNKNOWN_NATIVE_OBSERVATION")
        self.assertEqual(cohort.review_one("conditional_reset", (3, 1),
                                          dict(evidence, native_target=(3, 1))),
                         "DEMONSTRATED_DEFECT")


if __name__ == "__main__":
    unittest.main()
