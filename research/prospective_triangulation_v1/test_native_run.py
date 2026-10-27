"""Pin and native-observation protocol tests, run without external network."""
import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class NativeProtocolTests(unittest.TestCase):
    def test_independent_conventional_reference_matches_all_frozen_claims(self):
        conventional = importlib.import_module("reference")
        cohort = importlib.import_module("cohort")
        for case, inputs in cohort.full_population().items():
            for row in inputs:
                self.assertEqual(conventional.reference_output(case, row),
                                 cohort.contract_output(case, row), (case, row))

    def test_git_blob_pin_matches_real_bytes_and_rejects_mutation(self):
        native = importlib.import_module("native_run")
        self.assertEqual(native.git_blob_sha(b"hello\n"),
                         "ce013625030ba8dba906f756967f9e9ca394464a")
        with self.assertRaises(ValueError):
            native.check_pin(b"hello!\n", "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_missing_native_receipts_are_unknown_not_a_defect(self):
        native = importlib.import_module("native_run")
        self.assertEqual(native.grade_native_row("conditional_reset", (3, 1),
                                                None, (0, 1)),
                         "UNKNOWN_NATIVE_OBSERVATION")
        self.assertEqual(native.grade_native_row("conditional_reset", (3, 1),
                                                (0, 1), None),
                         "UNKNOWN_NATIVE_OBSERVATION")

    def test_native_output_row_parser_refuses_missing_extra_or_invalid_rows(self):
        native = importlib.import_module("native_run")
        rows = [(3, 0), (3, 1)]
        self.assertEqual(native.parse_native_rows("3 0\n0 1\n", rows, 2),
                         [(3, 0), (0, 1)])
        for text in ("3 0\n", "3 0\n0 1\n9 9\n", "3 x\n0 1\n", "3\n0 1\n"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    native.parse_native_rows(text, rows, 2)


if __name__ == "__main__":
    unittest.main()
