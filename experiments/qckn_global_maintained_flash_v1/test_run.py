from __future__ import annotations

import unittest

from experiments.qckn_global_maintained_flash_v1.run import run


class GlobalMaintainedFlashV1Tests(unittest.TestCase):
    def test_primary_verdict(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(
            r["scientific_verdict"],
            "PASS_GLOBAL_MAINTAINED_FLASH_FIXED_POINT",
        )

    def test_exact_cross_domain_edges_and_savings(self):
        r = run()
        g = r["global"]
        self.assertEqual(len(g["cross_domain_edges"]), 3)
        self.assertEqual(
            g["typed_avoided"],
            {
                "circuit.metric_checks": 6,
                "embodied.developmental_cost": 257,
                "opaque.verifier_calls": 187206,
            },
        )
        for d in ("circuit", "embodied", "opaque"):
            self.assertEqual(g["targets"][d]["status"], "RESOLVED")

    def test_arithmetic_fixed_point(self):
        r = run()
        a = r["global"]["arithmetic"]
        self.assertEqual(a["status"], "REVOKED_REOPENED_RECOMPILED")
        self.assertEqual(a["revocations"], 1)
        self.assertEqual(a["reopened_classes"], 101)
        self.assertEqual(a["final_classes"], 3)
        self.assertEqual(a["raw_reacquisition"], 0)
        self.assertEqual(a["runtime_authority_evaluations"], 202)
        self.assertGreaterEqual(r["global"]["waves"], 3)
        self.assertTrue(r["global"]["queue_empty"])

    def test_unlicensed_collatz_is_unchanged(self):
        r = run()
        c = r["global"]["collatz"]
        self.assertEqual(c["cross_domain_mutations"], 0)
        self.assertEqual(c["global_T_calls_avoided"], 0)
        self.assertFalse(any(e[1] == "collatz" for e in r["global"]["cross_domain_edges"]))

    def test_bus_controls(self):
        r = run()
        self.assertEqual(r["isolated"]["cross_domain_edges"], [])
        self.assertEqual(r["sham_bridge_control"]["cross_domain_edges"], [])
        for arm in ("isolated", "sham_bridge_control"):
            for d in ("circuit", "embodied", "opaque"):
                self.assertEqual(r[arm]["targets"][d]["status"], "COLD_COMPLETE")

    def test_revocation_and_reserve_controls(self):
        r = run()
        nr = r["no_revocation_control"]["arithmetic"]
        self.assertTrue(nr["unsoundness_detected"])
        self.assertEqual(nr["status"], "UNSOUND_OLD_QUOTIENT")
        nz = r["no_reserve_control"]["arithmetic"]
        self.assertTrue(nz["recovery_failed"])
        self.assertEqual(nz["reserve_entries"], 0)
        self.assertEqual(nz["status"], "RECOVERY_UNAVAILABLE")

    def test_restart_is_exact(self):
        r = run()
        self.assertEqual(r["restart_control"]["digest"], r["global"]["digest"])


if __name__ == "__main__":
    unittest.main()
