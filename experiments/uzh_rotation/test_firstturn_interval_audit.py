"""Causal source-audit tests; future heading must not seed first-turn data."""

import ctypes
from pathlib import Path
import tempfile
import unittest

from audit_firstturn_interval_capture import CONDITIONS, build_maps, generate_stream, load_gate
from audit_finite_partial_map import follow
from finite_witness_jitter import generate_jitter_trial


class FirstTurnReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="mathgraph-firstturn-replay-test-")
        cls.lib = load_gate(Path(cls.temp.name) / "libsource.so")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_capture_stream_ignores_all_future_heading_choices(self):
        for name in CONDITIONS:
            base = generate_jitter_trial(5, 0, "wide")
            for heading in (16, 32, 48):
                other = generate_jitter_trial(5, heading, "wide")
                self.assertEqual(base.physical_source, other.physical_source)
                self.assertEqual(generate_stream(base.physical_source, 5, name),
                                 generate_stream(other.physical_source, 5, name))

    def test_honest_sensor_bound_preserves_every_accepted_source_label(self):
        for seed in (5, 11):
            trial = generate_jitter_trial(seed, 0, "wide")
            for name, params in CONDITIONS.items():
                if params["lie"]:
                    continue
                records = generate_stream(trial.physical_source, seed, name)
                actual_error = lambda item: min(
                    (item[1] - item[0]) % 1024,
                    (item[0] - item[1]) % 1024,
                )
                self.assertTrue(all(actual_error(item) <= params["radius"]
                                    for item in records))
                gated, naive, diag = build_maps(self.lib, records,
                                               params["radius"])
                self.assertEqual(gated.frozen, 1)
                self.assertEqual(naive.frozen, 1)
                self.assertGreaterEqual(diag["deferred"], 0)
                for bin_idx in range(64):
                    if gated.seen[bin_idx // 8] & (1 << (bin_idx % 8)):
                        self.assertLessEqual((gated.columns[bin_idx] ^
                            trial.physical_source[bin_idx]).bit_count(), 1)

    def test_equally_informed_planner_and_continuous_baseline(self):
        trial = generate_jitter_trial(5, 32, "wide")
        stream = generate_stream(trial.physical_source, 5, "honest_r3_4x")
        gated, _, diag = build_maps(self.lib, stream, 3)
        self.assertGreaterEqual(gated.count, 40)
        for policy in ("active", "continuous"):
            outcome = follow(self.lib, gated, trial.columns, policy)
            self.assertNotEqual(outcome["status"], "CONFLICT", outcome)
            if outcome["status"] == "AUTHORIZED":
                self.assertEqual(outcome["accepted_bin"], 32)
        # An uncertainty radius spanning a full bin cannot form a reference.
        wide, _, wide_diag = build_maps(self.lib,
            generate_stream(trial.physical_source, 5, "honest_r8_4x"), 8)
        self.assertEqual(wide.count, 0)
        self.assertEqual(wide_diag["deferred"], 256)
        self.assertEqual(follow(self.lib, wide, trial.columns, "active")["status"],
                         "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
