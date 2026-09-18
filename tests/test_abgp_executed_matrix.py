import unittest


class ExecutedMatrixTests(unittest.TestCase):
    def api(self):
        from mathgraph.abgp.executed_matrix import run_executed_dev_matrix
        return run_executed_dev_matrix

    def test_matrix_uses_only_executed_generators_and_registered_analysis(self):
        result = self.api()(a_count=12, b_worlds_per_direction=3, g_worlds=6, p_count=4)
        self.assertEqual(result['mode'], 'DEV_EXECUTED_IMPLEMENTATION_QUALIFICATION')
        self.assertFalse(result['confirmatory_namespace_used'])
        self.assertFalse(result['freeze_authorized'])
        self.assertEqual(set(result['generator_kinds']), {'A', 'B', 'G', 'P'})
        self.assertEqual(result['generator_kinds'], {
            'A': 'executed_structural_construction',
            'B': 'independently_generated_cross_grammar',
            'G': 'causal_cell_evaluator_world_randomization',
            'P': 'hard_restart_source_distinct_structural_persistence',
        })
        self.assertEqual(set(result['analysis']['arms']), {'A', 'B', 'G', 'P'})
        self.assertTrue(all(result['analysis']['arms'][arm]['validity_pass'] for arm in 'ABGP'))

    def test_all_mechanical_hard_gates_are_executed_and_true(self):
        result = self.api()(a_count=12, b_worlds_per_direction=3, g_worlds=6, p_count=4)
        self.assertTrue(result['implementation_gates']['A'])
        self.assertTrue(result['implementation_gates']['B'])
        self.assertTrue(result['implementation_gates']['G'])
        self.assertTrue(result['implementation_gates']['P'])
        self.assertTrue(result['implementation_qualified'])
        self.assertFalse(result['complete_pass_power_qualified'])
        self.assertEqual(result['scientific_interpretation'], 'DEV_MECHANICS_AND_TEXT_IMPLEMENTATION_ONLY_NOT_CONFIRMATORY_EVIDENCE')

    def test_matrix_audits_earliest_generated_ancestors_without_overclaiming_independence(self):
        result = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        audits = result['inferential_ancestry_audit']
        self.assertEqual(set(audits), {'A', 'B', 'G', 'P'})
        for arm in 'ABGP':
            self.assertTrue(audits[arm]['no_shared_generated_ancestor_across_scored_units'])
            self.assertFalse(audits[arm]['statistical_independence_proved_by_this_audit'])
            self.assertTrue(audits[arm]['fixed_protocol_objects'])
        self.assertEqual(audits['B']['scored_unit_count'], 24)
        self.assertEqual(audits['B']['unique_latent_world_roots'], 24)

    def test_confirmation_namespace_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api()(a_count=4, b_worlds_per_direction=1, g_worlds=2, p_count=1,
                       namespace='ABGP-CONFIRM-v1')


if __name__ == '__main__':
    unittest.main()
