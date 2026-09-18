import json
import unittest
from pathlib import Path

from mathgraph.abgp.confirmatory import build_execution_lock
from mathgraph.abgp.executed_p_structural import (
    run_structural_p_batch,
    summarize_structural_p_episodes,
)
from mathgraph.abgp.manifest import active_seed_namespace, reset_development_namespace


class ConfirmatoryPlumbingTests(unittest.TestCase):
    def tearDown(self):
        reset_development_namespace()

    def test_execution_lock_binds_frozen_counts_without_activating_confirmatory_namespace(self):
        self.assertEqual(active_seed_namespace(), "ABGP-DEV-v1")
        lock = build_execution_lock("a" * 40)
        self.assertEqual(lock["status"], "FROZEN")
        self.assertTrue(lock["confirmatory_execution_enabled"])
        self.assertEqual(lock["confirmatory_namespace_identifier"], "ABGP-CONFIRM-v1")
        self.assertEqual(lock["approved_planning"]["counts"], {
            "A": 4096,
            "B_worlds_per_direction": 1015,
            "B_total_worlds": 12180,
            "G": 421,
            "P": 4096,
        })
        self.assertEqual(active_seed_namespace(), "ABGP-DEV-v1")
        self.assertEqual(len(lock["lock_digest"]), 64)

    def test_p_sharding_is_exactly_analysis_equivalent_under_dev_namespace(self):
        left = run_structural_p_batch(2, namespace="ABGP-DEV-v1", start_index=0)
        right = run_structural_p_batch(2, namespace="ABGP-DEV-v1", start_index=2)
        combined = summarize_structural_p_episodes(left["episodes"] + right["episodes"])
        direct = run_structural_p_batch(4, namespace="ABGP-DEV-v1", start_index=0)
        self.assertEqual(combined["analysis_input"], direct["analysis_input"])
        self.assertEqual(
            [row["episode_index"] for row in combined["episodes"]],
            [0, 1, 2, 3],
        )
        self.assertFalse(combined["confirmatory_namespace_used"])

    def test_execution_lock_has_fail_closed_one_shot_marker_policy(self):
        lock = build_execution_lock("b" * 40)
        policy = lock["one_shot_execution_marker_policy"]
        self.assertIn("STARTED marker", policy)
        self.assertIn("permanently blocks another run", policy)
        self.assertTrue(lock["execution_plumbing_only"])
        self.assertFalse(lock["scientific_code_change"])


if __name__ == "__main__":
    unittest.main()
