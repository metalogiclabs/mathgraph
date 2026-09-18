import unittest

from mathgraph.abgp.manifest import load_analysis_plan


class PlanningReviewTests(unittest.TestCase):
    def test_proposal_keeps_scientific_pass_floors_unchanged(self):
        from mathgraph.abgp.planning_review import build_planning_proposal
        plan = load_analysis_plan('preregistration/abgp-analysis-plan-v1.json')
        proposal = build_planning_proposal(plan)
        self.assertEqual(proposal['status'], 'FROZEN_APPROVED')
        self.assertTrue(proposal['complete_pass_power_qualified'])
        self.assertEqual(proposal['familywise_alpha'], 0.05)
        self.assertEqual(proposal['component_alpha'], 0.0125)
        self.assertEqual(proposal['arms']['A']['observed_pass_floor'], 0.05)
        self.assertEqual(proposal['arms']['B']['observed_pass_floor'], 0.15)
        self.assertEqual(proposal['arms']['G']['observed_pass_floor'], 0.15)
        self.assertEqual(proposal['arms']['P']['observed_pass_floor'], 0.05)

    def test_planning_alternatives_are_strictly_above_pass_floors(self):
        from mathgraph.abgp.planning_review import build_planning_proposal
        proposal = build_planning_proposal(load_analysis_plan('preregistration/abgp-analysis-plan-v1.json'))
        for arm in 'ABGP':
            self.assertGreater(proposal['arms'][arm]['planning_effect'], proposal['arms'][arm]['observed_pass_floor'])

    def test_rounded_counts_clear_conservative_eighty_percent_lower_bound(self):
        from mathgraph.abgp.planning_review import build_planning_proposal
        proposal = build_planning_proposal(load_analysis_plan('preregistration/abgp-analysis-plan-v1.json'))
        self.assertEqual(proposal['arms']['A']['proposed_n'], 4096)
        self.assertEqual(proposal['arms']['B']['proposed_worlds_per_direction'], 1015)
        self.assertEqual(proposal['arms']['B']['proposed_total_worlds'], 12180)
        self.assertEqual(proposal['arms']['G']['proposed_n'], 421)
        self.assertEqual(proposal['arms']['P']['proposed_n'], 4096)
        for arm in 'ABGP':
            self.assertGreaterEqual(proposal['arms'][arm]['conservative_complete_pass_lower_bound'], 0.80)

    def test_b_includes_90_percent_agreement_gate_without_counting_nested_interventions_as_n(self):
        from mathgraph.abgp.planning_review import build_planning_proposal
        proposal = build_planning_proposal(load_analysis_plan('preregistration/abgp-analysis-plan-v1.json'))
        b = proposal['arms']['B']
        self.assertEqual(b['planning_world_all_four_agreement'], 0.95)
        self.assertEqual(b['observed_pooled_agreement_gate'], 0.90)
        self.assertGreaterEqual(b['conservative_agreement_gate_power'], 0.80)
        self.assertEqual(b['independent_unit_count_for_agreement_planning'], 12180)
        self.assertEqual(b['interventions_per_world'], 4)

    def test_p_deletion_closeness_is_a_mechanical_assumption_not_fake_power(self):
        from mathgraph.abgp.planning_review import build_planning_proposal
        proposal = build_planning_proposal(load_analysis_plan('preregistration/abgp-analysis-plan-v1.json'))
        p = proposal['arms']['P']
        self.assertEqual(p['component_count'], 7)
        self.assertEqual(p['deletion_closeness_planning'], 'MECHANICALLY_IDENTICAL_TO_COLD_POTENTIAL_OUTCOME')
        self.assertTrue(proposal['approved_by_collaborators'])


if __name__ == '__main__':
    unittest.main()
