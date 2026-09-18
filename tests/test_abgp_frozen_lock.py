import json
import tempfile
import unittest
from pathlib import Path

from mathgraph.abgp.frozen_lock import build_frozen_lock, write_frozen_lock

class FrozenLockTests(unittest.TestCase):
    def test_frozen_lock_binds_approved_candidate_and_keeps_confirmation_disabled(self):
        lock = build_frozen_lock(
            repository_tree_hash="tree-test-123",
            repository_commit="commit-test-123",
            a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3,
        )
        self.assertEqual(lock["schema"], "abgp.frozen-lock.v1")
        self.assertEqual(lock["status"], "FROZEN")
        self.assertTrue(lock["freeze_authorized"])
        self.assertTrue(lock["joint_review_complete"])
        self.assertFalse(lock["confirmatory_execution_enabled"])
        self.assertFalse(lock["confirmatory_namespace_used"])
        self.assertEqual(lock["approved_candidate_digest"],
            "771793f52cc8228c54bf2ac8ab46ebbcb0c7a99284d94e3042951a7976921e04")
        self.assertEqual(lock["planning_status"], "FROZEN_APPROVED")
        self.assertTrue(lock["qualification_status"].startswith("IMPLEMENTATION_QUALIFIED"))
        self.assertEqual(len(lock["lock_digest"]), 64)
        self.assertTrue(all(len(v) == 64 for v in lock["bound_file_hashes"].values()))
        self.assertIn(".github/workflows/abgp-confirmatory-v1.yml", lock["bound_file_hashes"])
        self.assertIn("mathgraph/abgp/confirmatory.py", lock["bound_file_hashes"])
        self.assertIn("abgp_confirm.py", lock["bound_file_hashes"])

    def test_approved_planning_is_exact(self):
        lock = build_frozen_lock(
            repository_tree_hash="tree-test-123",
            repository_commit="commit-test-123",
            a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3,
        )
        approved = lock["approved_planning"]
        self.assertEqual(approved["effects"], {"A": 0.1, "B": 0.25, "G": 0.25, "P": 0.1})
        self.assertEqual(approved["counts"]["A"], 4096)
        self.assertEqual(approved["counts"]["B_worlds_per_direction"], 1015)
        self.assertEqual(approved["counts"]["G"], 421)
        self.assertEqual(approved["counts"]["P"], 4096)
        self.assertEqual(approved["B_all_four_world_agreement"], 0.95)
        self.assertEqual(approved["P_deletion_to_cold"],
                         "MECHANICALLY_IDENTICAL_TO_COLD_POTENTIAL_OUTCOME")

    def test_writer_is_canonical(self):
        lock = build_frozen_lock(
            repository_tree_hash="tree-test-123",
            repository_commit="commit-test-123",
            a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock.json"
            write_frozen_lock(path, lock)
            self.assertEqual(json.loads(path.read_text()), lock)

if __name__ == "__main__":
    unittest.main()
