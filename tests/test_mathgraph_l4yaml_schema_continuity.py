"""Adversarial controls for pinned source-native typed-schema replay."""

import json
import unittest

from research.l4yaml_semantic_diff_v2.schema_continuity import (
    CASES, typed_value, verify_native_rows,
)


class SchemaContinuityTests(unittest.TestCase):
    def setUp(self):
        self.expected = [
            {"input": source, "result": typed_value(value)}
            for (_, source), value in zip(CASES, ("true", True, "null", None, "42", 42,
                                                   "true", True))
        ]
        self.rows = [json.dumps(x) for x in self.expected]

    def test_eight_expected_cases_have_two_distinguishable_scalar_styles(self):
        self.assertEqual(len(CASES), 8)
        self.assertEqual(verify_native_rows(self.expected, self.rows)["matched"], 8)

    def test_missing_row_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "ROW_COUNT"):
            verify_native_rows(self.expected, self.rows[:-1])

    def test_reordered_row_fails_closed(self):
        rows = list(self.rows)
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaisesRegex(ValueError, "CASE_IDENTITY"):
            verify_native_rows(self.expected, rows)

    def test_semantically_wrong_value_fails_closed(self):
        rows = list(self.rows)
        wrong = dict(self.expected[0])
        wrong["result"] = typed_value(True)
        rows[0] = json.dumps(wrong)
        with self.assertRaisesRegex(ValueError, "SCHEMA_VALUE_MISMATCH"):
            verify_native_rows(self.expected, rows)

    def test_bool_integer_substitution_fails_closed(self):
        # Python equality alone would silently equate True with 1.
        rows = list(self.rows)
        forged = dict(self.expected[1])
        forged["result"] = {"kind": "bool", "value": 1}
        rows[1] = json.dumps(forged)
        with self.assertRaisesRegex(ValueError, "SCHEMA_VALUE_MISMATCH"):
            verify_native_rows(self.expected, rows)

    def test_duplicated_json_key_fails_closed(self):
        rows = list(self.rows)
        rows[0] = '{"input":"oops","input":"oops","result":{}}'
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            verify_native_rows(self.expected, rows)

    def test_non_json_scalar_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "SCHEMA_VALUE_UNSUPPORTED"):
            typed_value({"unhandled": True})


if __name__ == "__main__":
    unittest.main()
