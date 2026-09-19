from __future__ import annotations

import unittest

from experiments.qckn_probe_interface_genesis_v1.run import run


class ProbeInterfaceGenesisV1Tests(unittest.TestCase):
    def test_primary_verdict(self):
        r = run()
        self.assertTrue(r["gates"]["pass"])
        self.assertEqual(
            r["scientific_verdict"],
            "PASS_VERIFIED_PROBE_INTERFACE_GENESIS",
        )

    def test_probe_language_grows_only_when_needed(self):
        r = run()
        d = r["global"]["discovery"]
        self.assertEqual(d["hypothesis_counts"], [24, 2, 1])
        self.assertEqual(
            d["selected_probes"],
            ["empty", "one", "useful", "opened"],
        )
        self.assertEqual(d["synthesized_probes"], ["useful", "opened"])
        self.assertIn("two", d["unused_generated_probes"])

    def test_bridge_authority_is_separate_and_complete(self):
        r = run()
        d = r["global"]["discovery"]
        self.assertEqual(d["developmental_execution_evaluations"], 48)
        self.assertEqual(d["attack_execution_evaluations"], 72)
        self.assertEqual(d["attack_comparison_checks"], 216)
        self.assertEqual(r["global"]["bridge_authority_execution_evaluations"], 120)
        self.assertTrue(d["attack_passed"])

    def test_live_target_changes_only_after_certificate(self):
        r = run()
        g = r["global"]
        self.assertEqual(g["source_event_initial_edges"], 0)
        self.assertEqual(g["target_prefix_calls"], 35290)
        self.assertEqual(g["edge_count"], 1)
        self.assertEqual(g["target_suffix_calls"], 96)
        self.assertEqual(g["target_final_calls"], 35386)
        self.assertEqual(g["target_calls_avoided"], 187422)

    def test_static_and_sham_probe_languages_fail(self):
        r = run()
        static = r["static_language_control"]
        sham = r["sham_grammar_control"]
        self.assertFalse(static["discovery"]["proposed"])
        self.assertEqual(static["discovery"]["hypothesis_counts"], [24])
        self.assertFalse(sham["discovery"]["proposed"])
        self.assertEqual(sham["discovery"]["hypothesis_counts"], [24, 6])
        self.assertEqual(static["target_final_calls"], 222808)
        self.assertEqual(sham["target_final_calls"], 222808)

    def test_independent_attack_rejects_wrong_target(self):
        r = run()
        m = r["mismatch_target_control"]
        self.assertFalse(m["discovery"]["proposed"])
        self.assertEqual(
            m["discovery"]["obstruction"],
            "INDEPENDENT_ATTACK_FAILED",
        )
        self.assertEqual(m["target_final_calls"], 222808)

    def test_ambiguous_target_is_an_obstruction(self):
        r = run()
        a = r["ambiguous_target_control"]
        self.assertFalse(a["discovery"]["proposed"])
        self.assertEqual(
            a["discovery"]["obstruction"],
            "NO_BRIDGE_HYPOTHESIS_SURVIVES",
        )
        self.assertEqual(a["edge_count"], 0)

    def test_withhold_and_restart_controls(self):
        r = run()
        self.assertEqual(
            r["withheld_certificate_control"]["target_final_calls"],
            222808,
        )
        self.assertEqual(
            r["restart_control"]["discovery"]["certificate_id"],
            r["global"]["discovery"]["certificate_id"],
        )
        self.assertEqual(
            r["restart_control"]["active_edges"],
            r["global"]["active_edges"],
        )
        self.assertEqual(
            r["restart_control"]["target_final_calls"],
            r["global"]["target_final_calls"],
        )


if __name__ == "__main__":
    unittest.main()
