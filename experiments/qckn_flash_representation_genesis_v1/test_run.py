from __future__ import annotations

import unittest

from experiments.qckn_flash_representation_genesis_v1.run import run


class FlashRepresentationGenesisV1Tests(unittest.TestCase):
    def test_primary_flash_gate(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(
            r["scientific_verdict"],
            "PASS_CROSS_DOMAIN_FLASH_REPRESENTATION_GENESIS",
        )

    def test_late_arrival_changes_reachability(self):
        r = run()
        a = r["arms"]
        self.assertFalse(a["COLD"]["resolved"])
        self.assertEqual(a["COLD"]["candidate_metric_checks"], 12)
        self.assertTrue(a["FLASH"]["resolved"])
        self.assertEqual(a["FLASH"]["candidate_metric_checks"], 6)
        self.assertTrue(a["WARM"]["resolved"])
        self.assertEqual(a["WARM"]["candidate_metric_checks"], 0)

    def test_controls_do_not_reproduce(self):
        r = run()
        a = r["arms"]
        self.assertFalse(a["RAW_HISTORY"]["resolved"])
        self.assertEqual(a["RAW_HISTORY"]["candidate_metric_checks"], 12)
        self.assertTrue(a["SHAM_OVERFINE"]["sham_rejected"])
        self.assertFalse(a["SHAM_OVERFINE"]["resolved"])
        self.assertTrue(a["ABLATION"]["exact_ablation"])
        self.assertFalse(a["ABLATION"]["resolved"])

    def test_minimality_preserves_unrelated_block(self):
        r = run()
        warm_blocks = tuple(tuple(x) for x in r["arms"]["WARM"]["final_blocks"])
        self.assertIn((0xAA, 0xCC), warm_blocks)
        self.assertIn((0x8F,), warm_blocks)
        self.assertIn((0xEA,), warm_blocks)
        self.assertEqual(len(warm_blocks), 3)

    def test_exact_circuit_collision(self):
        r = run()
        collision = r["target"]["collision"]
        self.assertEqual(collision["exact_nand_sizes"], [2, 3])
        self.assertEqual(len(collision["shared_12_metric_signature"]), 12)
        self.assertEqual(
            r["target"]["preserved_control_block"]["exact_nand_size"], 0
        )


if __name__ == "__main__":
    unittest.main()
