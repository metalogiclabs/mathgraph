import importlib.util
import unittest
from mathgraph.abgp.dev_world import make_dev_world


class ExecutedGTests(unittest.TestCase):
    def api(self):
        name = 'mathgraph.abgp.executed_g'
        self.assertIsNotNone(importlib.util.find_spec(name), 'corruption needs actual reevaluation')
        return __import__(name, fromlist=['*'])

    def test_flip_is_computed_from_changed_evaluator_outputs(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        seen = []
        def evaluator(w):
            seen.append(w.comparative_cells[0].value)
            ids = tuple(a.action_id for a in w.actions)
            return ids if w.comparative_cells[0].value % 2 else tuple(reversed(ids))
        initial = world.comparative_cells[0].value
        result = api.evaluate_corruption(world, evaluator, {world.comparative_cells[0].cell_id: (initial + 1) % 2})
        self.assertEqual(result['flip'], 1)
        self.assertEqual(len(seen), 2)
        self.assertNotEqual(result['before'], result['after'])

    def test_relevance_is_evaluated_not_copied_from_cell_annotation(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        def evaluator(w):
            ids = tuple(a.action_id for a in w.actions)
            return ids if w.comparative_cells[-1].value % 2 else tuple(reversed(ids))
        result = api.audit_relevance(world, evaluator, range(7))
        self.assertEqual(result['actual_relevant_cell_ids'], [world.comparative_cells[-1].cell_id])
        self.assertFalse(result['declared_relevance_matches'])

    def test_existing_world_truth_has_no_cell_causal_dependence(self):
        api = self.api()
        world = make_dev_world('G', 1, 'abgp-g-dev-v1')
        audit = api.audit_relevance(world, api.legacy_world_order, range(7))
        self.assertEqual(len(audit['declared_relevant_cell_ids']), 10)
        self.assertEqual(audit['actual_relevant_cell_ids'], [])
        self.assertFalse(audit['eligible_matched_corruption_design'])
        self.assertGreater(audit['evaluations'], 100)

    def test_unknown_cell_is_rejected_instead_of_ignored(self):
        api = self.api()
        world = make_dev_world('G', 0, 'abgp-g-dev-v1')
        with self.assertRaises(ValueError):
            api.evaluate_corruption(world, api.legacy_world_order, {'nonexistent': 1})

    def test_structural_world_derives_relevance_from_actual_evaluator(self):
        api = self.api()
        world = api.make_structural_g_world(3, assignment=0)
        audit = api.audit_structural_relevance(world)
        self.assertEqual(len(audit['actual_relevant_cell_ids']), 10)
        self.assertEqual(set(audit['actual_relevant_cell_ids']), set(audit['declared_relevant_cell_ids']))
        self.assertTrue(audit['declared_relevance_matches'])
        self.assertTrue(audit['eligible_matched_corruption_design'])

    def test_structural_dose_outcomes_are_recomputed_not_planted(self):
        api = self.api()
        result = api.run_structural_g_world(4)
        self.assertEqual(result['evaluator_mode'], 'cell_causal')
        self.assertTrue(all(row['matched_count'] for row in result['dose_records']))
        self.assertTrue(all(row['relevant']['evaluator_calls'] == 2 for row in result['dose_records']))
        self.assertTrue(all(row['irrelevant']['evaluator_calls'] == 2 for row in result['dose_records']))
        self.assertEqual(result['max_dose_relevant_flip'], 1)
        self.assertEqual(result['max_dose_irrelevant_flip'], 0)

    def test_world_label_assignment_is_fair_and_selection_is_label_blind(self):
        api = self.api()
        audit = api.audit_g_randomization_design(6)
        self.assertEqual(audit['assignment_probabilities'], ['1/2', '1/2'])
        self.assertTrue(audit['same_base_world_under_both_assignments'])
        self.assertTrue(audit['pair_selection_identical_under_label_swap'])
        self.assertTrue(audit['fixed_complete_dose_schedule'])
        self.assertTrue(audit['no_adaptive_stopping'])
        self.assertTrue(audit['null_law_exchangeable'])
        self.assertTrue(audit['randomization_valid_under_registered_sharp_null'])

    def test_structural_batch_has_one_joint_block_per_world(self):
        api = self.api()
        batch = api.run_structural_g_batch(8)
        self.assertEqual(len(batch['worlds']), 8)
        self.assertEqual(len(batch['analysis_input']['max_dose_relevant']), 8)
        self.assertEqual(len(batch['analysis_input']['pairs']), 8 * 4)
        self.assertEqual({row['world_id'] for row in batch['analysis_input']['pairs']}, set(range(8)))
        self.assertTrue(batch['analysis_input']['hard_gates']['world_exchangeability_contract'])
        self.assertTrue(batch['analysis_input']['hard_gates']['same_evaluator'])


if __name__ == '__main__':
    unittest.main()
