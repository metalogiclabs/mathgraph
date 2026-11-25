import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location("axiom_experiment", Path(__file__).with_name("run.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AxiomAdmissionControls(unittest.TestCase):
    def test_exact_report_parser(self):
        self.assertEqual(module.inspect("target does not depend on any axioms\n"), set())
        self.assertEqual(module.inspect("target depends on axioms: [propext, Classical.choice]\n"),
                         {"propext", "Classical.choice"})
        for output in ["", "target depends on axioms: []", "unrelated depends on axioms: [x]"]:
            with self.assertRaises(ValueError):
                module.inspect(output)

    def test_controlled_five_case_dispositions(self):
        def fake_run(args, **kwargs):
            source = Path(args[-1]).read_text()
            if "private axiom hidden" in source:
                stdout = "target depends on axioms: [_private.fixture.hidden]\n"
            elif "axiom permitted" in source:
                stdout = "target depends on axioms: [permitted]\n"
            else:
                stdout = "target does not depend on any axioms\n"
            return subprocess.CompletedProcess(args, 0, stdout, "")
        with patch.object(module.subprocess, "run", side_effect=fake_run):
            rows = [module.run_case("lean", name, 30) for name in module.CASES]
        self.assertEqual([r["status"] for r in rows], [
            "OBSERVED_AGREEMENT", "OBSERVED_AGREEMENT", "OBSERVED_MISMATCH",
            "OBSERVED_AGREEMENT", "OBSERVED_MISMATCH"
        ])
        self.assertEqual(rows[2]["reason"], "UNAUTHORIZED_AXIOM_DEPENDENCY")

    def test_missing_tool_is_unknown(self):
        with patch.object(module.subprocess, "run", side_effect=FileNotFoundError()):
            row = module.run_case("not-a-tool", "benign", 30)
        self.assertEqual(row["status"], "UNKNOWN")

    def test_failed_compilation_is_unknown(self):
        with patch.object(module.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 1, "", "error")):
            row = module.run_case("lean", "private", 30)
        self.assertEqual(row["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
