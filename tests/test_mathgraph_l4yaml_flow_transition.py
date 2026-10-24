"""Source-derived scanner transition: exact witnesses, independent parser limits."""

import json
import unittest

from research.l4yaml_semantic_diff_v2.flow_transition import (
    CASES, classify_rows, summarize_transition,
)


class FlowTransitionTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(len(CASES), 19)
        self.old = [json.dumps({"input": source, "legacy": True, "indexed": True})
                    for _, source in CASES]
        self.new = [json.dumps({"input": source, "legacy": i >= 11, "indexed": i >= 11})
                    for i, (_, source) in enumerate(CASES)]

    def test_exact_observed_transition(self):
        old = classify_rows(self.old)
        new = classify_rows(self.new)
        delta = summarize_transition(old, new)
        self.assertEqual(delta["accepted_to_refused"], 11)
        self.assertEqual(delta["accepted_to_accepted"], 8)
        self.assertEqual(delta["legacy_indexed_disagreements"], 0)

    def test_one_missing_case_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "FLOW_ROW_COUNT"):
            classify_rows(self.old[:-1])

    def test_out_of_order_case_fails_closed(self):
        rows = self.old.copy()
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaisesRegex(ValueError, "FLOW_CASE_ORDER"):
            classify_rows(rows)

    def test_duplicate_key_fails_closed(self):
        rows = self.old.copy()
        rows[0] = '{"input":"x","input":"x","legacy":true,"indexed":true}'
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            classify_rows(rows)

    def test_legacy_indexed_difference_is_retained(self):
        rows = self.new.copy()
        rows[0] = json.dumps({"input": CASES[0][1], "legacy": False, "indexed": True})
        delta = summarize_transition(classify_rows(self.old), classify_rows(rows))
        self.assertEqual(delta["legacy_indexed_disagreements"], 1)
        # One ambiguous row is excluded rather than silently counted as changed.
        self.assertEqual(delta["accepted_to_refused"], 10)

    def test_unchanged_baseline_does_not_fabricate_repair(self):
        delta = summarize_transition(classify_rows(self.old), classify_rows(self.old))
        self.assertEqual(delta["accepted_to_refused"], 0)
        self.assertEqual(delta["accepted_to_accepted"], 19)


if __name__ == "__main__":
    unittest.main()
