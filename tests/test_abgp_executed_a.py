import unittest


class ExecutedATests(unittest.TestCase):
    def test_old_language_is_exhaustively_obstructed_but_constructor_finds_unique_xor(self):
        from mathgraph.abgp.executed_a import run_a_episode
        episode = run_a_episode(0)
        self.assertTrue(episode['old_language_complete'])
        self.assertEqual(episode['old_language_adequate_candidates'], 0)
        self.assertEqual(episode['constructed_reducer'], 'XOR_REDUCE')
        self.assertEqual(episode['constructor_survivor_count'], 1)
        self.assertGreater(episode['posterior_action_support'], 1)
        self.assertEqual(episode['verifier_message_count'], 1)
        self.assertFalse(episode['verifier_message_identifies_action'])

    def test_sealed_future_uses_new_representation_with_no_verifier(self):
        from mathgraph.abgp.executed_a import run_a_episode
        episode = run_a_episode(7)
        self.assertEqual(episode['future_verifier_calls'], 0)
        self.assertTrue(episode['acquisition_future_seed_disjoint'])
        self.assertEqual(episode['treatment_future_correct'], 1)
        self.assertIn(episode['fixed_language_bayes_future_correct'], (0, 1))
        self.assertIn(episode['sham_future_correct'], (0, 1))
        self.assertIn(episode['equal_recheck_future_correct'], (0, 1))

    def test_old_bayes_sees_same_source_observations_but_cannot_add_xor(self):
        from mathgraph.abgp.executed_a import run_a_batch
        result = run_a_batch(32)
        self.assertTrue(result['same_information_source_history'])
        self.assertTrue(result['same_verifier_message'])
        self.assertTrue(result['old_bayes_frozen_hypothesis_class'])
        self.assertTrue(result['representation_growth_gate'])
        self.assertEqual(result['future_verifier_calls'], 0)
        self.assertEqual(len(result['analysis_input']['treatment']), 32)
        self.assertEqual(set(result['analysis_input']['baselines']), {
            'fixed_language_bayes', 'sham_expansion', 'equal_compute_recheck'
        })

    def test_message_plus_constructor_visible_information_remains_nonidentifying(self):
        from mathgraph.abgp.executed_a import run_a_batch
        result = run_a_batch(16)
        self.assertGreaterEqual(result['minimum_constructor_visible_action_support'], 2)
        self.assertTrue(result['analysis_input']['hard_gates']['message_nonidentifying'])
        self.assertTrue(result['analysis_input']['hard_gates']['old_language_complete'])
        self.assertTrue(result['analysis_input']['hard_gates']['future_no_verifier'])


if __name__ == '__main__':
    unittest.main()
