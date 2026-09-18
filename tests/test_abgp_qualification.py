import json
import tempfile
import unittest
from pathlib import Path

from mathgraph.abgp.qualification import run_qualification, write_qualification_artifact


class ABGPQualificationTests(unittest.TestCase):
    def test_complete_qualification_is_deterministic_and_confirmatory_free(self):
        first = run_qualification()
        second = run_qualification()
        self.assertEqual(first, second)
        self.assertEqual(first["mode"], "QUALIFICATION_ONLY")
        self.assertFalse(first["confirmatory_namespace_used"])
        self.assertEqual(first["verdict"], "HARNESS_QUALIFIED")
        self.assertTrue(first["statistical_reference_audit"]["status"] == "PASS")
        self.assertTrue(first["power_audit"]["qualified"])
        self.assertTrue(all(row["matched_expectation"] for row in first["fixtures"]))
        self.assertTrue(all(row["observed_verdict"] == row["expected_verdict"] for row in first["fixtures"]))
        self.assertEqual(len(first["qualification_digest"]), 64)

    def test_artifact_round_trip_is_canonical(self):
        artifact = run_qualification()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qualification.json"
            write_qualification_artifact(path, artifact)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            parsed = json.loads(text)
            self.assertEqual(parsed, artifact)
            write_qualification_artifact(path, parsed)
            self.assertEqual(path.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
