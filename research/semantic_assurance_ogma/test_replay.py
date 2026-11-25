"""Consequential scope and admission controls for the real-source adapter."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.p = replay.load_protocol()
        self.facts = {"unpatched": {"qualified": True, "matches": False},
                      "patched": {"qualified": True, "matches": True}}

    def test_native_success_does_not_warrant_transfer(self):
        outcomes, states = replay.graph_decisions(self.facts, self.p)
        self.assertEqual(states["unpatched:native"], replay.WARRANTED)
        self.assertEqual(outcomes["unpatched"], replay.REJECTED)
        self.assertEqual(outcomes["patched"], replay.WARRANTED)

    def test_unqualified_receipt_labels_cannot_enable_adapter_routes(self):
        for fact in self.facts.values():
            fact["qualified"] = False
        outcomes, states = replay.graph_decisions(self.facts, self.p)
        self.assertEqual(set(outcomes.values()), {replay.UNKNOWN})
        self.assertEqual(states["patched:native"], replay.UNKNOWN)

    def test_source_withdrawal_is_unknown_and_preserves_native_observation(self):
        outcomes, states = replay.graph_decisions(self.facts, self.p,
                                                withdrawn=frozenset({"source"}))
        self.assertEqual(set(outcomes.values()), {replay.UNKNOWN})
        self.assertEqual(states["unpatched:native"], replay.WARRANTED)

    def test_native_evidence_withdrawal_is_selective_and_reversible(self):
        outcomes, _ = replay.graph_decisions(self.facts, self.p,
                                           withdrawn=frozenset({"patched:native"}))
        self.assertEqual(outcomes, {"unpatched": replay.REJECTED, "patched": replay.UNKNOWN})
        restored, _ = replay.graph_decisions(self.facts, self.p)
        self.assertEqual(restored["patched"], replay.WARRANTED)

    def test_changed_signal_and_deployment_scope_stay_unknown(self):
        domain = deepcopy(self.p["domain"])
        domain["signal"] = "kgs"
        for options in ({"domain": domain}, {"claim": "deployment_authorized"}):
            outcomes, _ = replay.graph_decisions(self.facts, self.p, **options)
            self.assertEqual(set(outcomes.values()), {replay.UNKNOWN})

    def test_history_is_not_an_instantaneous_threshold_test(self):
        self.assertEqual(replay.expected_counts(["0x1p+0", "-0x1p+0", "0x1p+0"]), [0, 1, 2])
        self.assertEqual(replay.expected_counts(["-0x0p+0", "0x0p+0"]), [0, 0])
        self.assertNotEqual(replay.input_bits(["-0x0p+0"]), replay.input_bits(["0x0p+0"]))

    def test_native_certificate_coverage_cannot_be_inferred_from_matching_rows(self):
        self.assertFalse(replay.verify_table([], Path("nonexistent-executable"), self.p))
        row = {"trace": ["0x0p+0"], "bits": ["00000000"], "callbacks": [0]}
        self.assertFalse(replay.verify_table([row] * len(replay.traces(self.p)),
                                            Path("nonexistent-executable"), self.p))


if __name__ == "__main__":
    unittest.main()
