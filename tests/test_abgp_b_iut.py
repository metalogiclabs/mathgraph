import unittest

from mathgraph.abgp.analysis import analyze_b


_DIRECTIONS = tuple(f"g{i}->g{j}" for i in range(4) for j in range(4) if i != j)


def _raw(worlds_per_direction: int = 32):
    labels = [direction for direction in _DIRECTIONS for _ in range(worlds_per_direction)]
    n = len(labels)
    return {
        "treatment": [1] * n,
        "wrong_class": [0] * n,
        "shuffled_coupling": [0] * n,
        "acquisition_posterior_target_bisimulation_bayes": [0] * n,
        "direction_labels": labels,
        "intervention_agreement": [1] * (n * 4),
        "hard_gates": {
            "grammar_independence": True,
            "no_translation": True,
            "all_12_ordered_directions": True,
        },
    }


class ABGPBIntersectionUnionTests(unittest.TestCase):
    def test_each_direction_control_pair_is_a_component_hypothesis(self):
        result = analyze_b(_raw())
        self.assertEqual(result["analysis_mode"], "DIRECTION_STRATIFIED_IUT")
        self.assertEqual(result["inferential_unit"], "ordered_direction_world_pair")
        self.assertEqual(result["direction_count"], 12)
        self.assertEqual(len(result["component_pvalues"]), 36)
        self.assertAlmostEqual(result["raw_pvalue"], 2.0 ** -32)
        self.assertEqual(result["effect"], 1.0)
        self.assertTrue(result["effect_floor_pass"])

    def test_one_failed_direction_control_component_fails_entire_iut(self):
        raw = _raw()
        target_direction = _DIRECTIONS[-1]
        for index, direction in enumerate(raw["direction_labels"]):
            if direction == target_direction:
                raw["acquisition_posterior_target_bisimulation_bayes"][index] = 1
        result = analyze_b(raw)
        self.assertEqual(result["raw_pvalue"], 1.0)
        self.assertEqual(result["effect"], 0.0)
        self.assertFalse(result["effect_floor_pass"])
        self.assertIn(
            f"{target_direction}|acquisition_posterior_target_bisimulation_bayes",
            result["component_pvalues"],
        )

    def test_interventions_are_nested_not_counted_as_independent_units(self):
        result = analyze_b(_raw(worlds_per_direction=5))
        self.assertEqual(result["unit_count"], 60)
        self.assertEqual(result["intervention_evaluations"], 240)
        self.assertEqual(result["interventions_per_unit"], 4)


if __name__ == "__main__":
    unittest.main()
