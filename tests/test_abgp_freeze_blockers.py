import inspect
import unittest
from dataclasses import replace

from mathgraph.abgp import arm_b
from mathgraph.abgp.arm_a import generate_a_growth_episodes
from mathgraph.abgp.arm_b import generate_b_dev_records
from mathgraph.abgp.arm_g import generate_g_dev_records
from mathgraph.abgp.arm_p import generate_p_independent_episodes
from mathgraph.abgp.freeze_review import (
    audit_a_stochastic_ancestry,
    audit_g_exchangeability_design,
    audit_p_stochastic_ancestry,
    freeze_power_review,
)
from mathgraph.abgp.manifest import load_analysis_plan


class ABGPFreezeBlockerTests(unittest.TestCase):
    def test_a_and_p_audit_earliest_shared_stochastic_ancestor(self):
        a = audit_a_stochastic_ancestry(generate_a_growth_episodes(64))
        p = audit_p_stochastic_ancestry(generate_p_independent_episodes(64))
        self.assertFalse(a["no_cross_episode_shared_stochastic_ancestor"])
        self.assertTrue(a["listed_seed_fields_disjoint"])
        self.assertFalse(p["no_cross_episode_shared_stochastic_ancestor"])
        self.assertTrue(p["listed_seed_fields_disjoint"])
        self.assertEqual(a["shared_stochastic_ancestor_count"], 0)
        self.assertEqual(p["shared_stochastic_ancestor_count"], 0)
        self.assertIn("fixed_protocol_objects", a)
        self.assertIn("fixed_protocol_objects", p)
        self.assertIn("earliest_stochastic_ancestor_rule", a)
        self.assertIn("earliest_stochastic_ancestor_rule", p)

    def test_b_records_use_real_recovery_and_real_bisimulation_control(self):
        source = inspect.getsource(arm_b)
        self.assertNotIn("recovered_order = target_order", source)
        records = generate_b_dev_records(4)
        self.assertTrue(records)
        self.assertTrue(all(record.recovery_path_verified for record in records))
        self.assertFalse(any(record.bisimulation_separation_witness for record in records))
        self.assertTrue(all(record.acquired_capability_digest for record in records))
        self.assertTrue(all(record.transfer_recovered_digest for record in records))
        self.assertTrue(all(record.bisimulation_control_digest for record in records))
        self.assertTrue(all(record.bisimulation_bayes_success == record.treatment_success for record in records))

    def test_power_audit_marks_alpha_provenance_and_complete_pass_scope(self):
        plan = load_analysis_plan("preregistration/abgp-analysis-plan-v1.json")
        audit = freeze_power_review(plan)
        self.assertEqual(
            audit["alpha_provenance"],
            "four_arm_familywise_holm_worst_case_component_alpha_not_b_iut_multiplicity",
        )
        self.assertFalse(audit["complete_pass_power_qualified"])
        for arm in ("A", "B", "P"):
            self.assertIn("complete_pass_power_status", audit["arms"][arm])
            self.assertIn("complete_component_power_at_declared_true_effect_floor", audit["arms"][arm])
            self.assertLess(
                audit["arms"][arm]["complete_component_power_at_declared_true_effect_floor"],
                0.55,
            )
        self.assertEqual(
            audit["resolution_required"],
            "jointly_freeze_a_planning_alternative_strictly_above_each_observed_pass_floor",
        )
        self.assertNotEqual(audit["arms"]["B"]["complete_pass_power_status"], "QUALIFIED")

    def test_g_exchangeability_contract_is_design_level_and_fail_closed(self):
        records = generate_g_dev_records(8)
        audit = audit_g_exchangeability_design(records)
        self.assertFalse(audit["joint_world_vector_exchangeability_under_null"])
        self.assertFalse(audit["selection_fixed_before_outcomes"])
        self.assertFalse(audit["generation_label_symmetric_under_null"])
        self.assertFalse(audit["no_adaptive_stopping"])
        self.assertTrue(audit["matched_pair_construction"])
        self.assertTrue(audit["matched_pair_selection_label_swap_invariant"])
        self.assertFalse(audit["sharp_null_vector_swap_invariance"])
        self.assertEqual(audit["null_model"], "UNBOUND")

        broken = list(records)
        target = next(i for i, record in enumerate(broken) if record.dose > 0)
        broken[target] = replace(
            broken[target],
            irrelevant_corruption_count=broken[target].irrelevant_corruption_count + 1,
        )
        broken_audit = audit_g_exchangeability_design(broken)
        self.assertFalse(broken_audit["joint_world_vector_exchangeability_under_null"])


if __name__ == "__main__":
    unittest.main()
