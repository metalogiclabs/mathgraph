import unittest


class ExecutedBTests(unittest.TestCase):
    def api(self):
        from mathgraph.abgp import executed_b
        return executed_b

    def test_four_families_have_no_surface_or_primitive_dictionary(self):
        api = self.api()
        grammars = [api.make_grammar(fid, 3, 'source') for fid in api.FAMILY_IDS]
        self.assertEqual(len(grammars), 4)
        self.assertEqual(len({len(g.primitives) for g in grammars}), 4)
        for i, left in enumerate(grammars):
            for right in grammars[i + 1:]:
                self.assertTrue(set(left.surface_symbols).isdisjoint(right.surface_symbols))
                self.assertTrue(set(left.primitives).isdisjoint(right.primitives))
                self.assertNotEqual(len(left.primitives), len(right.primitives))
        self.assertEqual(len({g.serialization_schema for g in grammars}), 4)
        self.assertEqual(len({g.inference_route for g in grammars}), 4)

    def test_same_family_regenerates_new_surface_without_changing_behavioral_class(self):
        api = self.api()
        g0 = api.make_grammar('extensional', 2, 'source')
        g1 = api.make_grammar('extensional', 9, 'target')
        self.assertTrue(set(g0.surface_symbols).isdisjoint(g1.surface_symbols))
        world = api.make_world(5)
        r0 = g0.encode(world, 'baseline')
        r1 = g1.encode(world, 'baseline')
        self.assertEqual(api.behavioral_signatures(g0.decode(r0)), api.behavioral_signatures(g1.decode(r1)))
        self.assertNotEqual(api.digest(r0), api.digest(r1))

    def test_acquisition_learns_class_not_literal_tokens(self):
        api = self.api()
        result = api.run_b_direction('extensional', 'reachability', 7)
        self.assertEqual(result['candidate_capability_count'], 24)
        self.assertEqual(result['surviving_capability_count'], 1)
        self.assertTrue(result['source_target_surface_disjoint'])
        self.assertTrue(result['no_primitive_dictionary'])
        self.assertNotEqual(result['source_representation_digest'], result['target_representation_digests'][0])
        self.assertEqual(result['treatment_success'], 1)
        self.assertEqual(len(result['intervention_results']), 4)
        self.assertTrue(all(row['agreement'] for row in result['intervention_results']))

    def test_old_bisimulation_merges_states_that_new_capability_separates(self):
        api = self.api()
        result = api.run_b_direction('compositional', 'constraint_order', 11)
        self.assertEqual(result['old_bisimulation_class_count'], 1)
        self.assertTrue(result['bisimulation_separation_witness'])
        self.assertEqual(result['old_bisimulation_bayes_success'], 0)
        self.assertEqual(result['treatment_success'], 1)

    def test_all_twelve_directions_use_fresh_generated_grammars(self):
        api = self.api()
        records = api.run_b_batch(3)
        self.assertEqual(len(records), 36)
        self.assertEqual(len({(r['acquisition_family'], r['transfer_family']) for r in records}), 12)
        self.assertEqual(len({r['source_grammar_digest'] for r in records}), 36)
        self.assertEqual(len({r['target_grammar_digest'] for r in records}), 36)
        self.assertEqual(len({r['latent_world_digest'] for r in records}), 36)
        self.assertTrue(all(r['grammar_independence'] for r in records))
        self.assertTrue(all(r['bisimulation_separation_witness'] for r in records))

    def test_wrong_class_and_shuffled_coupling_are_executed_not_seed_bits(self):
        api = self.api()
        records = api.run_b_batch(4)
        self.assertTrue(all(r['wrong_class_success'] == 0 for r in records))
        self.assertTrue(any(r['shuffled_coupling_success'] == 0 for r in records))
        self.assertTrue(all(r['control_execution']['wrong_class_candidate'] for r in records))
        self.assertTrue(all(r['control_execution']['shuffled_source_world_digest'] for r in records))


if __name__ == '__main__':
    unittest.main()
