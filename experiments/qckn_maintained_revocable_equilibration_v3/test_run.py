from __future__ import annotations

import unittest

from experiments.qckn_maintained_revocable_equilibration_v3.run import run


class MaintainedRevocableEquilibrationV3Tests(unittest.TestCase):
    def test_primary_verdict(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(
            r["scientific_verdict"],
            "PASS_INCREMENTAL_REVOCABLE_CONSEQUENTIAL_EQUILIBRATION",
        )

    def test_incremental_runtime_authority(self):
        r = run()
        f = r["flash"]
        self.assertEqual(f["initial_runtime_authority_evaluations"], 101)
        self.assertEqual(f["expanded_runtime_authority_evaluations"], 101)
        self.assertEqual(f["total_runtime_authority_evaluations"], 202)
        self.assertAlmostEqual(
            r["economics"]["runtime_check_reduction_fraction_vs_repeated_v2_pairwise"],
            0.98,
            places=12,
        )

    def test_reserve_and_revocation(self):
        r = run()
        f = r["flash"]
        self.assertEqual(f["initial_active_classes"], 2)
        self.assertEqual(f["reserve_entries_after_stream"], 101)
        self.assertEqual(f["revocation_count"], 1)
        self.assertEqual(f["reopened_classes"], 101)
        self.assertEqual(f["raw_reacquisition_count"], 0)
        self.assertEqual(f["final_active_classes"], 3)

    def test_restart_is_exact(self):
        r = run()
        self.assertTrue(r["flash"]["restart_exact"])
        self.assertTrue(r["restart_control"]["restart_exact"])
        self.assertEqual(r["restart_control"]["final_active_classes"], 3)
        self.assertEqual(r["restart_control"]["revocation_count"], 1)

    def test_negative_controls(self):
        r = run()
        self.assertTrue(r["no_reserve_control"]["recovery_failed"])
        self.assertTrue(r["no_revocation_control"]["unsoundness_detected"])
        witness = r["no_revocation_control"]["witness"]
        self.assertIsNotNone(witness)
        self.assertNotEqual(
            witness["new_consequences"][0],
            witness["new_consequences"][1],
        )

    def test_scope_change_is_real(self):
        r = run()
        self.assertTrue(r["new_obligation"]["outside_old_scope"])
        self.assertEqual(r["new_obligation"]["expected_expanded_classes"], 3)
        self.assertEqual(r["flash"]["audit_positive_count"], 1)


if __name__ == "__main__":
    unittest.main()
