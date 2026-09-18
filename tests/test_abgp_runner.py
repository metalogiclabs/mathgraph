import json
import tempfile
import unittest
from pathlib import Path

from mathgraph.abgp.analysis import analyze_matrix
from mathgraph.abgp.manifest import ConfirmatoryLockedError
from mathgraph.abgp.runner import run_dev_matrix, run_matrix, write_dev_summary


class ABGPRunnerTests(unittest.TestCase):
    def test_dev_matrix_is_raw_replayable_and_confirmatory_free(self):
        summary = run_dev_matrix(a_count=32, b_worlds_per_direction=4, g_worlds=16, p_count=32)
        self.assertEqual(summary["mode"], "DEV_ONLY")
        self.assertFalse(summary["confirmatory_namespace_used"])
        self.assertFalse(summary["design"]["confirmatory_execution_enabled"])
        self.assertEqual(summary["design"]["status"], "FROZEN")
        serialized_records = json.dumps(summary["raw_records"], sort_keys=True)
        self.assertNotIn("ABGP-CONFIRM-v1", serialized_records)
        replay = analyze_matrix(summary["analysis_inputs"])
        self.assertEqual(replay, summary["analysis"])

    def test_dev_matrix_uses_hardened_a_and_p_inferential_units(self):
        summary = run_dev_matrix(a_count=48, b_worlds_per_direction=2, g_worlds=8, p_count=48)
        a = summary["analysis"]["arms"]["A"]
        self.assertEqual(a["analysis_mode"], "STRENGTHENED_REPRESENTATION_GROWTH")
        self.assertTrue(summary["audits"]["A"]["fresh_future_seed_separation"])
        self.assertEqual(summary["audits"]["A"]["future_verifier_calls"], 0)

        p_audit = summary["audits"]["P"]
        self.assertEqual(p_audit["inferential_unit"], "independent_acquisition_episode")
        self.assertEqual(p_audit["primary_n"], 48)
        self.assertEqual(p_audit["future_tasks_per_episode"], 4)
        self.assertTrue(p_audit["nested_tasks_not_counted_as_n"])
        self.assertTrue(p_audit["only_retained_object_crosses_restart"])
        self.assertEqual(summary["analysis"]["arms"]["P"]["analysis_mode"], "INDEPENDENT_EPISODE_POSTERIOR_BISIMULATION")

    def test_dev_matrix_records_zero_search_and_verifier_persistence_audit(self):
        summary = run_dev_matrix(a_count=16, b_worlds_per_direction=2, g_worlds=8, p_count=16)
        audit = summary["audits"]["P"]
        self.assertEqual(audit["future_verifier_calls"], 0)
        self.assertEqual(audit["future_reconstruction_search_count"], 0)
        self.assertTrue(audit["all_source_distinct"])
        self.assertTrue(audit["all_label_free"])
        self.assertGreater(audit["reacquisition_search_count_after_deletion"], 0)

    def test_summary_file_is_canonical_and_replayable(self):
        summary = run_dev_matrix(a_count=12, b_worlds_per_direction=1, g_worlds=6, p_count=12)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.json"
            write_dev_summary(path, summary)
            first = path.read_text(encoding="utf-8")
            parsed = json.loads(first)
            write_dev_summary(path, parsed)
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            self.assertEqual(analyze_matrix(parsed["analysis_inputs"]), parsed["analysis"])

    def test_confirmatory_namespace_is_rejected_before_generation(self):
        with self.assertRaises(ConfirmatoryLockedError):
            run_matrix(namespace="ABGP-CONFIRM-v1")


if __name__ == "__main__":
    unittest.main()
