"""Predeclared native construction and equally informed baseline tests."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
import unittest

from run_native import prepare_cases
from conventional_baseline import compare


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get("MATHGRAPH_TLA_SOURCE_DIR")
        if not source:
            raise unittest.SkipTest("pinned public source checkout not available")
        cls.source = Path(source)

    def test_precisely_one_mutation_and_weaker_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = {p.name: p.read_bytes() for p in self.source.glob("*") if p.is_file()}
            prepare_cases(self.source, root)
            self.assertEqual((root / "author" / "LamportMutex.tla").read_bytes(),
                             (self.source / "LamportMutex.tla").read_bytes())
            self.assertEqual((root / "author" / "MCLamportMutex.cfg").read_bytes(),
                             (self.source / "MCLamportMutex.cfg").read_bytes())
            self.assertEqual((root / "mutant_checked" / "LamportMutex.tla").read_bytes(),
                             (root / "mutant_weakened" / "LamportMutex.tla").read_bytes())
            self.assertNotEqual((root / "author" / "LamportMutex.tla").read_bytes(),
                                (root / "mutant_checked" / "LamportMutex.tla").read_bytes())
            mutant_model = (root / "mutant_checked" / "LamportMutex.tla").read_text()
            self.assertIn("  /\\ ack[p] = Proc\n", mutant_model)
            self.assertNotIn("  /\\ \\A q \\in Proc \\ {p} : beats(p,q)\n",
                             mutant_model)
            checked = (root / "mutant_checked" / "MCLamportMutex.cfg").read_text()
            weak = (root / "mutant_weakened" / "MCLamportMutex.cfg").read_text()
            self.assertIn("INVARIANTS TypeOK BoundedNetwork Mutex", checked)
            self.assertIn("INVARIANTS TypeOK BoundedNetwork\n", weak)
            self.assertNotIn("INVARIANTS TypeOK BoundedNetwork Mutex", weak)
            self.assertEqual(before, {p.name: p.read_bytes()
                                      for p in self.source.glob("*") if p.is_file()})

    def test_source_aware_baseline_detects_omission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_cases(self.source, root)
            for name, log, rc in [
                ("author", "Model checking completed. No error has been found.\n", 0),
                ("mutant_checked", "Error: Invariant Mutex is violated.\n", 12),
                ("mutant_weakened", "Model checking completed. No error has been found.\n", 0),
            ]:
                (root / name / "tlc.log").write_text(log)
                (root / name / "tlc.exit").write_text(str(rc) + "\n")
            result = compare(self.source, root)
            self.assertEqual(result["author"], "WARRANTED_BOUNDED")
            self.assertEqual(result["mutant_checked"], "COUNTERMODEL")
            self.assertEqual(result["mutant_weakened"], "REFUSED_UNCHECKED_PROPERTY")
            self.assertEqual(result["relative_advantage"], "BASELINE_TIE")

    def test_source_aware_baseline_withdraws_for_tampered_author_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_copy = Path(tmp) / "source"
            shutil.copytree(self.source, source_copy)
            root = Path(tmp) / "cases"
            prepare_cases(self.source, root)
            source_model = source_copy / "LamportMutex.tla"
            source_model.write_text(source_model.read_text().replace(
                "TLA+ specification of Lamport's distributed mutual-exclusion algorithm",
                "Altered description of Lamport's distributed mutual-exclusion algorithm"))
            result = compare(source_copy, root)
            self.assertEqual(result["relative_advantage"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
