from __future__ import annotations

import unittest

from experiments.qckn_bridge_genesis_v1.run import run


class BridgeGenesisV1Tests(unittest.TestCase):
    def test_primary_verdict(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(r["scientific_verdict"], "PASS_VERIFIED_BRIDGE_GENESIS")

    def test_bridge_is_not_predeclared(self):
        r = run()
        g = r["global"]
        self.assertTrue(g["source_event_had_zero_edges_before_genesis"])
        self.assertEqual(g["target_cold_prefix_calls"], 35290)
        self.assertEqual(g["edge_count"], 1)

    def test_unique_complete_bijection(self):
        r = run()
        d = r["global"]["discovery"]
        self.assertTrue(d["admitted"])
        self.assertTrue(d["complete_probe_basis"])
        self.assertTrue(d["unique_target"])
        self.assertTrue(d["unique_bijection"])
        self.assertEqual(len(d["mapping"]), 6)
        self.assertEqual(d["behavior_probe_calls"], 864)
        self.assertEqual(
            set(d["rejected_interfaces"]),
            {"opaque-mismatch-v1", "opaque-ambiguous-v1"},
        )

    def test_live_target_collapses_after_bridge(self):
        r = run()
        g = r["global"]
        self.assertEqual(g["target_suffix_calls_after_bridge"], 96)
        self.assertEqual(g["target_final_verifier_calls"], 35386)
        self.assertEqual(g["target_calls_avoided"], 187422)
        self.assertEqual(g["status"], "RESOLVED_BY_DISCOVERED_BRIDGE")

    def test_controls_block_propagation(self):
        r = run()
        self.assertEqual(
            r["withheld_certificate_control"]["target_final_verifier_calls"],
            222808,
        )
        self.assertFalse(r["incomplete_probe_control"]["discovery"]["admitted"])
        self.assertFalse(r["no_exact_target_control"]["discovery"]["admitted"])
        self.assertFalse(r["ambiguous_destination_control"]["discovery"]["admitted"])
        self.assertEqual(r["incomplete_probe_control"]["edge_count"], 0)
        self.assertEqual(r["no_exact_target_control"]["edge_count"], 0)
        self.assertEqual(r["ambiguous_destination_control"]["edge_count"], 0)

    def test_restart_reproduces_bridge(self):
        r = run()
        a = r["global"]
        b = r["restart_control"]
        self.assertEqual(a["target_final_verifier_calls"], b["target_final_verifier_calls"])
        self.assertEqual(a["active_bus_edges"], b["active_bus_edges"])
        self.assertEqual(
            a["discovery"]["certificate_id"],
            b["discovery"]["certificate_id"],
        )


if __name__ == "__main__":
    unittest.main()
