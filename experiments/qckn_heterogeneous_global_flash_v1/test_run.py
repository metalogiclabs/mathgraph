from __future__ import annotations

import unittest

from experiments.qckn_heterogeneous_global_flash_v1.run import run


class HeterogeneousGlobalFlashV1Tests(unittest.TestCase):
    def test_exact_costs_are_seed_stable(self):
        for seed in range(32):
            result = run(seed)
            arms = result["arms"]
            self.assertEqual(arms["COLD"]["developmental_cost"], 518)
            self.assertEqual(arms["RAW_SHARED"]["developmental_cost"], 518)
            self.assertEqual(arms["ABLATION"]["developmental_cost"], 518)
            self.assertEqual(arms["UPFRONT"]["developmental_cost"], 5)
            self.assertEqual(arms["FLASH"]["developmental_cost"], 261)
            self.assertEqual(arms["SHAM"]["developmental_cost"], 789)
            self.assertTrue(result["gates"]["pass"])

    def test_flash_is_late_not_upfront(self):
        result = run(7)
        flash = result["arms"]["FLASH"]
        self.assertGreater(flash["cold_prefix_evaluations"], 0)
        self.assertEqual(result["target"]["arrival_after_interventions"], 1)
        self.assertGreater(
            flash["developmental_cost"],
            result["arms"]["UPFRONT"]["developmental_cost"],
        )
        self.assertLess(
            flash["developmental_cost"],
            result["arms"]["COLD"]["developmental_cost"],
        )

    def test_sham_and_ablation_controls(self):
        result = run(11)
        self.assertTrue(result["arms"]["SHAM"]["transferred_rejected"])
        self.assertEqual(
            result["arms"]["ABLATION"]["developmental_cost"],
            result["arms"]["COLD"]["developmental_cost"],
        )
        self.assertEqual(
            result["arms"]["RAW_SHARED"]["developmental_cost"],
            result["arms"]["COLD"]["developmental_cost"],
        )

    def test_unlicensed_domains_do_not_move(self):
        result = run(19)
        self.assertTrue(result["spectators"])
        for row in result["spectators"]:
            self.assertEqual(row["before"], "LIVE")
            self.assertEqual(row["after"], "LIVE")
            self.assertIn("NO_VERIFIED", row["reason"])


if __name__ == "__main__":
    unittest.main()
