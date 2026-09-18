import unittest


class StructuralPersistenceTests(unittest.TestCase):
    def api(self):
        from mathgraph.abgp import executed_p_structural
        return executed_p_structural

    def test_acquisition_uniquely_identifies_parity_capability(self):
        api = self.api()
        episode = api.run_structural_p_episode(0)
        self.assertEqual(episode['acquisition']['candidate_count'], 8)
        self.assertEqual(episode['acquisition']['survivor_count'], 1)
        self.assertEqual(episode['acquisition']['retained']['capability'], 'PARITY_DIFFERENCE')
        self.assertGreater(episode['acquisition']['candidate_checks'], 0)

    def test_future_is_source_distinct_and_label_free(self):
        api = self.api()
        episode = api.run_structural_p_episode(3)
        audit = episode['source_distinctness']
        self.assertTrue(audit['source_future_surface_tokens_disjoint'])
        self.assertTrue(audit['source_future_serialization_distinct'])
        self.assertTrue(audit['source_future_exact_structures_distinct'])
        self.assertTrue(audit['future_instance_ids_disjoint'])
        self.assertFalse(audit['future_payload_contains_target_labels'])
        self.assertTrue(audit['label_free_applicability'])

    def test_retained_invocation_has_no_acquisition_search_or_verifier(self):
        api = self.api()
        episode = api.run_structural_p_episode(5)
        for receipt in episode['runs']['retained']:
            self.assertFalse(receipt['acquisition_code_loaded'])
            self.assertEqual(receipt['trace']['candidate_checks'], 0)
            self.assertEqual(receipt['trace']['source_example_reads'], 0)
            self.assertEqual(receipt['trace']['verifier_calls'], 0)

    def test_deletion_restores_cold_and_reacquisition_restores_capability(self):
        api = self.api()
        episode = api.run_structural_p_episode(7)
        self.assertEqual(episode['scores']['retained'], 1)
        self.assertEqual(episode['scores']['cold'], 0)
        self.assertEqual(episode['scores']['deleted'], episode['scores']['cold'])
        self.assertEqual(episode['scores']['reacquired'], episode['scores']['retained'])
        self.assertTrue(episode['runs']['deletion']['removed'])
        self.assertGreater(episode['runs']['reacquire']['candidate_checks'], 0)

    def test_exact_old_posterior_gets_same_source_history_but_does_not_gain_new_relation(self):
        api = self.api()
        episode = api.run_structural_p_episode(9)
        self.assertEqual(
            episode['acquisition']['source_history_digest'],
            episode['runs']['old_posterior']['source_history_digest'],
        )
        self.assertEqual(episode['runs']['old_posterior']['old_state'], 'FIRST_LAST_EQUALITY')
        self.assertEqual(episode['runs']['old_posterior']['posterior_counts'], {'equal': [4, 4], 'different': [4, 4]})
        self.assertEqual(episode['scores']['old_posterior'], 0)
        self.assertEqual(episode['scores']['retained'], 1)

    def test_four_future_probes_are_nested_one_episode_outcome(self):
        api = self.api()
        episode = api.run_structural_p_episode(11)
        self.assertEqual(len(episode['future_tasks']), 4)
        self.assertEqual([task['length'] for task in episode['future_tasks']], [6, 8, 10, 12])
        self.assertEqual(episode['future_task_count'], 4)
        self.assertEqual(episode['inferential_unit'], 'acquisition_restart_future_episode')
        self.assertEqual(episode['scores']['retained'], int(all(episode['probe_scores']['retained'])))

    def test_batch_preserves_negative_and_primary_controls(self):
        api = self.api()
        batch = api.run_structural_p_batch(16)
        self.assertEqual(len(batch['episodes']), 16)
        self.assertTrue(all(e['scores']['retained'] == 1 for e in batch['episodes']))
        self.assertTrue(all(e['scores']['old_posterior'] == 0 for e in batch['episodes']))
        self.assertTrue(all(e['scores']['deleted'] == e['scores']['cold'] for e in batch['episodes']))
        self.assertTrue(all(e['scores']['reacquired'] == 1 for e in batch['episodes']))
        self.assertTrue(batch['hard_gates']['zero_verifier'])
        self.assertTrue(batch['hard_gates']['zero_search'])
        self.assertTrue(batch['hard_gates']['source_distinct'])
        self.assertTrue(batch['hard_gates']['restart_clean'])

    def test_batch_exposes_exact_registered_baseline_set(self):
        api = self.api()
        batch = api.run_structural_p_batch(4)
        self.assertEqual(set(batch['analysis_input']['baselines']), {
            'cold', 'equal_compute_recheck', 'verbal_rule_negative',
            'size_matched_sham', 'wrong_class_object',
            'target_only_bisimulation_bayes', 'posterior_only_retained_bayes',
            'targeted_deletion',
        })

    def test_other_namespaces_remain_inaccessible(self):
        api = self.api()
        with self.assertRaises(ValueError):
            api.run_structural_p_batch(2, namespace='ABGP-CONFIRM-v1')


if __name__ == '__main__':
    unittest.main()
