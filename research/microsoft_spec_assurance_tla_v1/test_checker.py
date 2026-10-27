"""Tests for exact-source, fail-closed specification assurance.

The fabricated TLC text here is only a unit-test fixture. The CI workflow also
runs the actual TLC binary and retains its native logs before adjudication.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from independent_checker import assess, SOURCE_PIN, TLC_SHA256


GOOD_LOG = (
    "TLC2 Version 2026.10.26.231022\n"
    "Parsing file /controlled/MCLamportMutex.tla\n"
    "Model checking completed. No error has been found.\n"
    "123 states generated, 99 distinct states found, 0 states left on queue.\n"
    "Finished in 1s\n"
)
BAD_LOG = (
    "TLC2 Version 2026.10.26.231022\n"
    "Parsing file /controlled/MCLamportMutex.tla\n"
    "Error: Invariant Mutex is violated.\n"
    "The behavior up to this point is:\n"
    "State 1: <Initial predicate>\n"
    "State 2: <Enter(1)>\n"
    "State 3: <Enter(2)>\n"
    "/\\ crit = {1, 2}\n"
)


class CheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get("MATHGRAPH_TLA_SOURCE_DIR")
        if not source:
            raise unittest.SkipTest("set MATHGRAPH_TLA_SOURCE_DIR to pinned external checkout")
        cls.source = Path(source)
        assert (cls.source / "LamportMutex.tla").is_file()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tla-assurance-test-")
        self.root = Path(self.temp.name)
        model = (self.source / "LamportMutex.tla").read_text()
        cfg = (self.source / "MCLamportMutex.cfg").read_text()
        wrapper = (self.source / "MCLamportMutex.tla").read_text()
        guards = "  /\\ \\A q \\in Proc \\ {p} : beats(p,q)\n"
        self.assertEqual(model.count(guards), 1)
        mutant = model.replace(guards, "  /\\ TRUE\n")
        smaller = cfg.replace("N = 3", "N = 2").replace(
            "MaxNat = 7", "MaxNat = 4").replace("maxClock = 6", "maxClock = 3")
        weaker = smaller.replace("INVARIANTS TypeOK BoundedNetwork Mutex",
                                 "INVARIANTS TypeOK BoundedNetwork")
        self.assertNotEqual(weaker, smaller)
        for name, source_model, config, log, exitcode in [
            ("author", model, cfg, GOOD_LOG, 0),
            ("mutant_checked", mutant, smaller, BAD_LOG, 12),
            ("mutant_weakened", mutant, weaker, GOOD_LOG, 0),
        ]:
            folder = self.root / name
            folder.mkdir()
            (folder / "LamportMutex.tla").write_text(source_model)
            (folder / "MCLamportMutex.tla").write_text(wrapper)
            (folder / "MCLamportMutex.cfg").write_text(config)
            (folder / "tlc.log").write_text(log)
            (folder / "tlc.exit").write_text(str(exitcode) + "\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_scoped_author_positive_and_weakened_mutant_refused(self):
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "WARRANTED_BOUNDED_AUTHOR_MODEL", result)
        self.assertEqual(result["mutant_checked"], "FINITE_COUNTERMODEL")
        self.assertEqual(result["mutant_weakened"], "REJECTED_MISSING_MUTEX_GATE")
        self.assertFalse(result["general_proof"])

    def test_stale_source_withdraws(self):
        result = assess(self.source, self.root, "0" * 40, TLC_SHA256)
        self.assertEqual(result["authority"], "WITHDRAWN", result)

    def test_different_binary_rejects(self):
        result = assess(self.source, self.root, SOURCE_PIN, "0" * 64)
        self.assertEqual(result["authority"], "REJECTED_EVIDENCE")

    def test_missing_log_withdraws(self):
        (self.root / "author" / "tlc.log").unlink()
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "WITHDRAWN")

    def test_forged_mutant_success_rejected(self):
        (self.root / "mutant_checked" / "tlc.log").write_text(GOOD_LOG)
        (self.root / "mutant_checked" / "tlc.exit").write_text("0\n")
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "REJECTED_EVIDENCE")

    def test_forged_error_without_unsafe_critical_set_rejected(self):
        path = self.root / "mutant_checked" / "tlc.log"
        path.write_text(path.read_text().replace("/\\ crit = {1, 2}",
                                                 "/\\ crit = {1}"))
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "REJECTED_EVIDENCE")

    def test_wrong_original_config_rejected(self):
        path = self.root / "author" / "MCLamportMutex.cfg"
        path.write_text(path.read_text().replace(" Mutex", ""))
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "REJECTED_EVIDENCE")

    def test_model_mutant_not_silently_changed(self):
        path = self.root / "mutant_weakened" / "LamportMutex.tla"
        path.write_text(path.read_text().replace("crit' = crit \\union {p}",
                                                 "crit' = crit"))
        result = assess(self.source, self.root, SOURCE_PIN, TLC_SHA256)
        self.assertEqual(result["authority"], "REJECTED_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
