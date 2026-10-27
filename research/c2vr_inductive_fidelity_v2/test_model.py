import unittest

from model import audit_models, axioms_hold, least_relation


class InductiveSemanticsTests(unittest.TestCase):
    def test_constructor_closure_and_negative_witness(self):
        least = least_relation(3)
        self.assertIn((3, 0, 3), least)
        self.assertIn((3, 2, 1), least)
        self.assertNotIn((2, 0, 1), least)
        self.assertTrue(axioms_hold(least, 3))

    def test_total_relation_is_another_model_of_introduction_axioms(self):
        total = {(a, b, d) for a in range(4) for b in range(4) for d in range(4)}
        self.assertTrue(axioms_hold(total, 3))
        self.assertIn((2, 0, 1), total)

    def test_audit_preserves_two_distinct_models(self):
        report = audit_models(3)
        self.assertEqual(report['verdict'], 'FINITE_COUNTERMODEL')
        self.assertEqual(report['separating_query'], [2, 0, 1])
        self.assertEqual(report['source_query'], False)
        self.assertEqual(report['target_compatible_query'], True)
        self.assertTrue(report['both_satisfy_introduction_axioms'])

    def test_prevents_degenerate_bound(self):
        with self.assertRaises(ValueError):
            audit_models(1)


if __name__ == '__main__':
    unittest.main()
