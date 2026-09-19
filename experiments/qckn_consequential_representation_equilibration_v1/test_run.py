from __future__ import annotations

import unittest

from experiments.qckn_consequential_representation_equilibration_v1.run import run


class ConsequentialRepresentationEquilibrationV1Tests(unittest.TestCase):
    def test_same_operator_moves_both_directions(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(r["circuit_world"]["move"], "REFINE")
        self.assertEqual(r["lean_world"]["move"], "COARSEN")

    def test_circuit_flash(self):
        r = run()
        a = r["circuit_world"]["arms"]
        self.assertTrue(a["WARM"]["resolved"])
        self.assertEqual(a["WARM"]["metric_checks"], 0)
        self.assertTrue(a["FLASH"]["resolved"])
        self.assertEqual(a["FLASH"]["metric_checks"], 6)
        self.assertFalse(a["COLD"]["resolved"])
        self.assertEqual(a["COLD"]["metric_checks"], 12)
        self.assertTrue(a["SHAM_DISCRETE"]["sham_rejected"])

    def test_lean_flash(self):
        r = run()
        a = r["lean_world"]["arms"]
        self.assertEqual((a["COLD"]["misses"], a["COLD"]["hits"]), (8, 0))
        self.assertEqual((a["WARM"]["misses"], a["WARM"]["hits"]), (2, 6))
        self.assertEqual((a["FLASH"]["misses"], a["FLASH"]["hits"]), (3, 5))
        self.assertEqual(a["FLASH"]["move"], "COARSEN")
        self.assertTrue(a["SHAM_ALL_MERGED"]["sham_rejected"])
        self.assertEqual(a["ABLATION"]["misses"], 8)

    def test_controls_restore_cold(self):
        r = run()
        c = r["circuit_world"]["arms"]
        l = r["lean_world"]["arms"]
        self.assertEqual(c["RAW_HISTORY"]["metric_checks"], c["COLD"]["metric_checks"])
        self.assertFalse(c["RAW_HISTORY"]["resolved"])
        self.assertEqual(l["RAW_HISTORY"]["misses"], l["COLD"]["misses"])
        self.assertEqual(l["ABLATION"]["misses"], l["COLD"]["misses"])


if __name__ == "__main__":
    unittest.main()
