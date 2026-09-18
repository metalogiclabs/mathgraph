import copy
import json
import unittest
from pathlib import Path

from mathgraph.abgp.lock import build_review_lock, validate_final_lock
from mathgraph.abgp.manifest import load_analysis_plan, load_design_manifest


DESIGN_PATH = "preregistration/abgp-design-manifest-v1.json"
ANALYSIS_PATH = "preregistration/abgp-analysis-plan-v1.json"
TEMPLATE_PATH = Path("preregistration/abgp-final-lock-template-v1.json")


class ABGPLockTests(unittest.TestCase):
    def setUp(self):
        self.design = load_design_manifest(DESIGN_PATH)
        self.analysis = load_analysis_plan(ANALYSIS_PATH)
        self.files = {
            "mathgraph/abgp/analysis.py": "analysis-v1\n",
            "mathgraph/abgp/arm_a.py": "arm-a-v1\n",
            "mathgraph/abgp/arm_b.py": "arm-b-v1\n",
            "mathgraph/abgp/arm_g.py": "arm-g-v1\n",
            "mathgraph/abgp/arm_p.py": "arm-p-v1\n",
            "mathgraph/abgp/runner.py": "runner-v1\n",
        }
        self.runtime = {
            "repository_tree_hash": "tree-abc",
            "verifier_implementation_hash": "verifier-abc",
            "protected_evaluator_hash": "evaluator-abc",
            "grammar_family_generator_hashes": {"B": "grammars-abc"},
            "sham_object_construction_hash": "sham-abc",
            "wrong_class_construction_hash": "wrong-abc",
            "corruption_implementation_hash": "corrupt-abc",
            "ablation_implementation_hash": "ablate-abc",
            "ordinary_explanation_oracle_hashes": {"A": "oracle-a", "B": "oracle-b", "P": "oracle-p"},
            "bisimulation_canonicalizer_hashes": {"B": "bisim-b", "P": "bisim-p"},
            "inferential_unit_audit_hashes": {"A": "unit-a", "B": "unit-b", "G": "unit-g", "P": "unit-p"},
            "qualification_status": "QUALIFIED",
            "qualification_evidence_digest": "a" * 64,
            "model_and_runtime_versions": {"python": "3.12"},
            "dependency_environment_hash": "env-abc",
            "resource_budgets": {"cpu_seconds": 10},
            "confirmatory_namespace_identifier": "ABGP-CONFIRM-v1",
            "one_shot_execution_marker_policy": "single completion marker per lock digest",
        }

    def test_review_lock_contains_all_required_digest_material_and_stays_disabled(self):
        lock = build_review_lock(self.files, self.runtime)
        self.assertEqual(lock["status"], "REVIEW_PENDING")
        self.assertFalse(lock["confirmatory_execution_enabled"])
        self.assertEqual(lock["design_manifest_digest"], self.design.digest)
        self.assertEqual(lock["analysis_implementation_hash"], lock["scientific_code_hashes"]["mathgraph/abgp/analysis.py"])
        self.assertEqual(set(lock["arm_generator_code_hashes"]), {"A", "B", "G", "P"})
        self.assertEqual(lock["qualification_status"], "QUALIFIED")
        self.assertEqual(len(lock["qualification_evidence_digest"]), 64)
        for field in self.design.raw["final_lock_requirements"]:
            self.assertIn(field, lock)

    def test_scientific_code_change_changes_review_lock_digest(self):
        first = build_review_lock(self.files, self.runtime)
        changed = dict(self.files)
        changed["mathgraph/abgp/arm_g.py"] = "arm-g-v2\n"
        second = build_review_lock(changed, self.runtime)
        self.assertNotEqual(first["scientific_code_hashes"]["mathgraph/abgp/arm_g.py"], second["scientific_code_hashes"]["mathgraph/abgp/arm_g.py"])
        self.assertNotEqual(first["lock_digest"], second["lock_digest"])

    def test_validate_rejects_review_pending_missing_hashes_and_tree_mismatch(self):
        review = build_review_lock(self.files, self.runtime)
        with self.assertRaises(ValueError):
            validate_final_lock(review, self.design, self.analysis)

        frozen = copy.deepcopy(review)
        frozen["status"] = "FROZEN"
        frozen["confirmatory_execution_enabled"] = True
        frozen["repository_tree_hash"] = "different-tree"
        with self.assertRaises(ValueError):
            validate_final_lock(frozen, self.design, self.analysis, expected_tree_hash="tree-abc")

        missing = copy.deepcopy(frozen)
        missing["repository_tree_hash"] = "tree-abc"
        del missing["verifier_implementation_hash"]
        with self.assertRaises(ValueError):
            validate_final_lock(missing, self.design, self.analysis, expected_tree_hash="tree-abc")

    def test_review_builder_has_no_freeze_switch(self):
        lock = build_review_lock(self.files, self.runtime)
        self.assertNotIn("freeze", lock)
        self.assertNotIn("unlock", lock)
        self.assertNotEqual(lock["status"], "FROZEN")

    def test_review_lock_rejects_nonqualified_metadata(self):
        runtime = dict(self.runtime)
        runtime["qualification_status"] = "NOT_QUALIFIED"
        lock = build_review_lock(self.files, runtime)
        frozen = copy.deepcopy(lock)
        frozen["status"] = "FROZEN"
        frozen["confirmatory_execution_enabled"] = True
        with self.assertRaises(ValueError):
            validate_final_lock(frozen, self.design, self.analysis)

    def test_committed_lock_template_is_review_only_and_complete(self):
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(template["schema"], "mathgraph.abgp.final-lock-review-template.v1")
        self.assertEqual(template["status"], "REVIEW_PENDING")
        self.assertFalse(template["confirmatory_execution_enabled"])
        self.assertFalse(template["builder_can_freeze"])
        self.assertEqual(
            tuple(template["required_fields"]),
            tuple(self.design.raw["final_lock_requirements"]),
        )


if __name__ == "__main__":
    unittest.main()
