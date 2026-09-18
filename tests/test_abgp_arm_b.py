import unittest

from mathgraph.abgp.arm_b import (
    CompositionalGrammar,
    ConstraintOrderGrammar,
    ExtensionalGrammar,
    ReachabilityGrammar,
    generate_b_dev_records,
    grammar_families,
)


class ABGPArmBTests(unittest.TestCase):
    def test_grammar_families_are_structurally_independent(self):
        families = grammar_families()
        self.assertEqual(len(families), 4)
        alphabets = [set(g.surface_alphabet) for g in families]
        for i, left in enumerate(alphabets):
            for right in alphabets[i + 1 :]:
                self.assertTrue(left.isdisjoint(right))
        self.assertEqual(len({g.serialization_schema for g in families}), 4)
        self.assertGreater(len({g.primitive_arities for g in families}), 1)
        self.assertEqual(len({len(g.primitives) for g in families}), 4)
        self.assertEqual(len({g.inference_route for g in families}), 4)
        for grammar in families:
            self.assertIsNone(grammar.translation_table)

    def test_all_twelve_ordered_directions_and_four_interventions_exist(self):
        records = generate_b_dev_records(3)
        self.assertEqual(len(records), 12 * 3)
        directions = {(r.acquisition_family, r.transfer_family) for r in records}
        self.assertEqual(len(directions), 12)
        for record in records:
            self.assertNotEqual(record.acquisition_family, record.transfer_family)
            self.assertEqual(
                tuple(name for name, _ in record.intervention_results),
                (
                    "edge_or_relation_deletion",
                    "protected_order_reversal_perturbation",
                    "scope_change",
                    "constraint_change",
                ),
            )
            self.assertEqual(len(record.intervention_results), 4)
            self.assertTrue(record.seed_digest)

    def test_wrong_class_and_shuffled_controls_are_explicit(self):
        records = generate_b_dev_records(4)
        self.assertTrue(any(r.treatment_success != r.wrong_class_success for r in records))
        self.assertTrue(any(r.treatment_success != r.shuffled_coupling_success for r in records))
        for record in records:
            self.assertIn(record.wrong_class_success, (0, 1))
            self.assertIn(record.shuffled_coupling_success, (0, 1))

    def test_b_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_b_dev_records(2), generate_b_dev_records(2))


if __name__ == "__main__":
    unittest.main()
