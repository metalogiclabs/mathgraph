import importlib.util
import unittest


class AncestryTests(unittest.TestCase):
    def api(self):
        name = 'mathgraph.abgp.ancestry'
        self.assertIsNotNone(importlib.util.find_spec(name), 'need runtime provenance, not only listed seed fields')
        return __import__(name, fromlist=['*'])

    def test_shared_grandparent_detected_beneath_distinct_draws(self):
        a = self.api()
        ledger = a.Ledger()
        grammar = ledger.sample('shared-grammar', lambda: 7)
        x = ledger.sample('episode-0', lambda: 1, parents=(grammar,))
        y = ledger.sample('episode-1', lambda: 2, parents=(grammar,))
        audit = ledger.audit({'e0': (x,), 'e1': (y,)})
        self.assertFalse(audit['structurally_disjoint_random_ancestors'])
        self.assertIn(grammar.node_id, audit['shared_sampled_ancestors'])
        self.assertEqual(audit['independent_cluster_count'], 1)

    def test_equal_independently_drawn_values_do_not_create_fake_clusters(self):
        a = self.api()
        ledger = a.Ledger()
        x = ledger.sample('draw0', lambda: 0)
        y = ledger.sample('draw1', lambda: 0)
        audit = ledger.audit({'e0': (x,), 'e1': (y,)})
        self.assertTrue(audit['structurally_disjoint_random_ancestors'])
        self.assertEqual(audit['independent_cluster_count'], 2)
        self.assertFalse(audit['statistical_independence_proved'])

    def test_fixed_protocol_can_be_shared_but_random_constructor_cannot(self):
        a = self.api()
        ledger = a.Ledger()
        protocol = ledger.fixed('code', 'fixed-hash')
        x = ledger.sample('x', lambda: 0, parents=(protocol,))
        y = ledger.sample('y', lambda: 1, parents=(protocol,))
        audit = ledger.audit({'a': (x,), 'b': (y,)})
        self.assertTrue(audit['structurally_disjoint_random_ancestors'])
        constructor = ledger.sample('learned-constructor', lambda: 'weights')
        left = ledger.apply('future-a', lambda p, c: p, x, constructor)
        right = ledger.apply('future-b', lambda p, c: p, y, constructor)
        audit = ledger.audit({'a': (left,), 'b': (right,)})
        self.assertEqual(audit['independent_cluster_count'], 1)

    def test_same_event_reused_in_different_roles_is_detected(self):
        a = self.api()
        ledger = a.Ledger()
        root = ledger.sample('root', lambda: 1)
        source = ledger.apply('acquisition', lambda x: x + 1, root)
        future = ledger.apply('future', lambda x: x + 2, root)
        self.assertFalse(ledger.audit({'e0': (source,), 'e1': (future,)})['structurally_disjoint_random_ancestors'])

    def test_untracked_and_foreign_dependencies_are_rejected(self):
        a = self.api()
        ledger = a.Ledger()
        foreign = a.Ledger().sample('x', lambda: 1)
        with self.assertRaises(ValueError):
            ledger.apply('bad', lambda x: x, foreign)
        with self.assertRaises(ValueError):
            ledger.apply('bad', lambda x: x, 7)
        with self.assertRaises(ValueError):
            ledger.audit({'e': ()})

    def test_repeated_draw_name_cannot_conceal_shared_state(self):
        a = self.api()
        ledger = a.Ledger()
        ledger.sample('same-name', lambda: 1)
        with self.assertRaises(ValueError):
            ledger.sample('same-name', lambda: 2)


if __name__ == '__main__':
    unittest.main()
