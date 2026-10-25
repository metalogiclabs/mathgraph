"""Guard evidence cockpit against source/provenance confusion and HTML injection."""
import unittest
from separating_cockpit import render
from separating_experiments import run_demo

class SeparatingCockpitTests(unittest.TestCase):
    def test_reproduced_evidence_visible(self):
        html=render(run_demo())
        self.assertIn("MathGraph found the missing test",html)
        self.assertIn("clamp(-1, -2, 5)",html)
        self.assertIn("clamp(12, 0, 12)",html)
        self.assertIn("NOT A NEBIUS INFERENCE",html)
        self.assertIn("WARRANTED",html)
        self.assertIn("REJECTED",html)

    def test_rejects_unsupported_provenance(self):
        report=run_demo()
        report["provider"]="nebius-token-factory"
        with self.assertRaisesRegex(ValueError,"provenance"):
            render(report)

    def test_rejects_unsupported_schema(self):
        report=run_demo()
        report["schema"]="unknown"
        with self.assertRaisesRegex(ValueError,"schema"):
            render(report)

    def test_escapes_adversarial_event_content(self):
        report=run_demo()
        report["timeline"][0]["step"]='</strong><script>alert(1)</script>'
        html=render(report)
        self.assertNotIn("<script>alert(1)</script>",html)
        self.assertIn("&lt;script&gt;",html)

    def test_rejects_noninteger_case(self):
        report=run_demo()
        report["basis"]["tests"][0]=["<img onerror=alert(1)>",0,1]
        with self.assertRaisesRegex(ValueError,"testcase"):
            render(report)

if __name__ == "__main__":
    unittest.main()
