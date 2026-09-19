from __future__ import annotations

import unittest

from experiments.qckn_consequential_representation_equilibration_v2.run import run


class ConsequentialRepresentationEquilibrationV2Tests(unittest.TestCase):
    def test_bidirectional_operator(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(r["circuit_world"]["move"], "REFINE")
        self.assertEqual(r["arithmetic_world"]["move"], "COARSEN")

    def test_circuit_flash_and_controls(self):
        r = run()
        a = r["circuit_world"]["arms"]
        self.assertTrue(a["FLASH"]["resolved"])
        self.assertEqual(a["FLASH"]["diagnostic_checks"], 6)
        self.assertFalse(a["COLD"]["resolved"])
        self.assertEqual(a["COLD"]["diagnostic_checks"], 12)
        self.assertTrue(a["SHAM_DISCRETE"]["sham_rejected"])
        self.assertTrue(a["ABLATION"]["exact_ablation"])

    def test_arithmetic_coarsening(self):
        r = run()
        a = r["arithmetic_world"]["arms"]
        self.assertEqual(r["arithmetic_world"]["old_classes"], 101)
        self.assertEqual(r["arithmetic_world"]["target_classes"], 2)
        self.assertEqual(a["COLD"]["record_allocations"], 101)
        self.assertEqual(a["WARM"]["record_allocations"], 2)
        self.assertEqual(a["FLASH"]["record_allocations"], 22)
        self.assertEqual(a["FLASH"]["raw_allocations_before_flash"], 20)
        self.assertEqual(a["FLASH"]["final_classes"], 2)

    def test_arithmetic_controls(self):
        r = run()
        a = r["arithmetic_world"]["arms"]
        self.assertEqual(a["RAW_HISTORY"]["record_allocations"], 101)
        self.assertTrue(a["SHAM_ALL_MERGED"]["sham_rejected"])
        self.assertTrue(a["ABLATION"]["exact_ablation"])
        self.assertEqual(a["ABLATION"]["final_classes"], 101)


if __name__ == "__main__":
    unittest.main()
