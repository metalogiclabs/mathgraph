import unittest

class FinalCandidateTests(unittest.TestCase):
    def test_review_candidate_builder_is_closed_after_freeze(self):
        from mathgraph.abgp.final_candidate import build_final_lock_candidate
        with self.assertRaises(ValueError):
            build_final_lock_candidate(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)

    def test_frozen_normative_files_bind_approved_candidate(self):
        from mathgraph.abgp.manifest import load_analysis_plan, load_design_manifest
        design = load_design_manifest("preregistration/abgp-design-manifest-v1.json")
        plan = load_analysis_plan("preregistration/abgp-analysis-plan-v1.json")
        self.assertEqual(design.status, "FROZEN")
        self.assertEqual(plan.status, "FROZEN")
        self.assertFalse(design.confirmatory_execution_enabled)
        self.assertEqual(
            design.raw["final_lock_approval"]["approved_candidate_digest"],
            "771793f52cc8228c54bf2ac8ab46ebbcb0c7a99284d94e3042951a7976921e04",
        )
        self.assertEqual(design.raw["final_lock_approval"]["status"], "APPROVED")
        self.assertEqual(plan.raw["joint_approval"]["status"], "APPROVED")

    def test_confirmation_remains_locked_after_freeze(self):
        from mathgraph.abgp.manifest import ConfirmatoryLockedError, reject_confirmatory_namespace
        with self.assertRaises(ConfirmatoryLockedError):
            reject_confirmatory_namespace("ABGP-CONFIRM-v1", final_lock={
                "status": "FROZEN",
                "confirmatory_execution_enabled": False,
            })

if __name__ == "__main__":
    unittest.main()
