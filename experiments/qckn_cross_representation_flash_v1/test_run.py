from __future__ import annotations

import unittest

from experiments.qckn_cross_representation_flash_v1.run import run


class CrossRepresentationFlashV1Tests(unittest.TestCase):
    def test_primary_costs(self):
        r = run()
        a = r["arms"]
        self.assertEqual(a["COLD"]["verifier_calls"], 222808)
        self.assertEqual(a["UPFRONT"]["verifier_calls"], 320)
        self.assertEqual(a["FLASH"]["verifier_calls"], 35602)
        self.assertEqual(a["RAW_HISTORY"]["verifier_calls"], 222808)
        self.assertEqual(a["ABLATION"]["verifier_calls"], 222808)
        self.assertEqual(a["ANSWER_MEMORY_ONLY"]["verifier_calls"], 222808)
        self.assertEqual(a["SHAM_REDUNDANT_MACRO"]["verifier_calls"], 530562)
        self.assertTrue(r["gates"]["pass"])

    def test_live_arrival_is_real(self):
        r = run()
        self.assertEqual(r["schedule"]["arrival_after_completed_cold_depth"], 6)
        self.assertEqual(r["schedule"]["cold_prefix_verifier_calls"], 35290)
        self.assertEqual(r["arms"]["FLASH"]["post_event_calls"], 312)
        self.assertGreater(r["arms"]["FLASH"]["verifier_calls"], r["arms"]["UPFRONT"]["verifier_calls"])
        self.assertLess(r["arms"]["FLASH"]["verifier_calls"], r["arms"]["COLD"]["verifier_calls"])

    def test_controls_restore_or_worsen_cold(self):
        r = run()
        cold = r["arms"]["COLD"]["verifier_calls"]
        self.assertEqual(r["arms"]["RAW_HISTORY"]["verifier_calls"], cold)
        self.assertEqual(r["arms"]["ABLATION"]["verifier_calls"], cold)
        self.assertEqual(r["arms"]["ANSWER_MEMORY_ONLY"]["verifier_calls"], cold)
        self.assertGreater(r["arms"]["SHAM_REDUNDANT_MACRO"]["verifier_calls"], cold)

    def test_disjoint_surface_and_exact_avoidance(self):
        r = run()
        self.assertTrue(r["gates"]["source_surface_disjoint"])
        self.assertEqual(r["avoided_verifier_calls"], 187206)
        self.assertAlmostEqual(r["avoided_fraction"], 187206 / 222808, places=12)


if __name__ == "__main__":
    unittest.main()
