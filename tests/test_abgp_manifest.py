import unittest
from pathlib import Path

from mathgraph.abgp.manifest import (
    ConfirmatoryLockedError,
    derive_dev_seed,
    load_analysis_plan,
    load_design_manifest,
    reject_confirmatory_namespace,
)


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "preregistration" / "abgp-design-manifest-v1.json"
ANALYSIS_PATH = ROOT / "preregistration" / "abgp-analysis-plan-v1.json"


class ABGPManifestTests(unittest.TestCase):
    def test_dev_seed_is_deterministic_and_namespace_separated(self):
        a = derive_dev_seed("A", "task", 7, "gen-v1")
        b = derive_dev_seed("A", "task", 7, "gen-v1")
        c = derive_dev_seed("A", "task", 8, "gen-v1")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)

    def test_confirmatory_namespace_is_unavailable_without_frozen_lock(self):
        with self.assertRaises(ConfirmatoryLockedError):
            reject_confirmatory_namespace("ABGP-CONFIRM-v1", final_lock=None)

    def test_frozen_manifest_keeps_confirmation_disabled(self):
        design = load_design_manifest(DESIGN_PATH)
        self.assertEqual(design.status, "FROZEN")
        self.assertFalse(design.confirmatory_execution_enabled)
        self.assertEqual(design.development_namespace, "ABGP-DEV-v1")
        self.assertEqual(design.confirmatory_namespace, "ABGP-CONFIRM-v1")
        self.assertEqual(len(design.digest), 64)

    def test_analysis_plan_is_normative_and_frozen(self):
        plan = load_analysis_plan(ANALYSIS_PATH)
        self.assertTrue(plan.normative)
        self.assertEqual(plan.status, "FROZEN")
        self.assertEqual(plan.familywise_alpha, 0.05)
        self.assertEqual(tuple(plan.primary_arms), ("A", "B", "G", "P"))
        self.assertEqual(len(plan.digest), 64)
        self.assertTrue(plan.raw["qualification"]["approved_planning"]["approved"])
        self.assertEqual(plan.raw["qualification"]["approved_planning"]["effects"],
                         {"A": 0.10, "B": 0.25, "G": 0.25, "P": 0.10})

    def test_non_confirmatory_namespace_is_rejected_too(self):
        with self.assertRaises(ValueError):
            reject_confirmatory_namespace("some-other-namespace", final_lock=None)


if __name__ == "__main__":
    unittest.main()
