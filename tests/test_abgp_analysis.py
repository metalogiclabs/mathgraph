import itertools
import unittest

from mathgraph.abgp.analysis import (
    analyze_a,
    analyze_b,
    analyze_g,
    analyze_matrix,
    analyze_p,
    exact_mcnemar_one_sided,
    g_exact_randomization_pvalue,
    g_world_blocked_randomization_pvalue,
    holm_bonferroni,
)


class ABGPAnalysisTests(unittest.TestCase):
    def test_exact_mcnemar_known_cases(self):
        self.assertEqual(exact_mcnemar_one_sided([]), 1.0)
        self.assertEqual(exact_mcnemar_one_sided([(0, 1)]), 0.5)
        self.assertAlmostEqual(
            exact_mcnemar_one_sided([(0, 1), (0, 1), (1, 0)]),
            0.5,
        )
        self.assertAlmostEqual(
            exact_mcnemar_one_sided([(0, 1)] * 5),
            1.0 / 32.0,
        )

    def test_holm_uses_deterministic_arm_name_ties(self):
        adjusted = holm_bonferroni(
            {"P": 0.01, "G": 0.01, "B": 0.01, "A": 0.01},
            0.05,
        )
        self.assertEqual(tuple(adjusted["order"]), ("A", "B", "G", "P"))
        self.assertAlmostEqual(adjusted["adjusted_pvalues"]["A"], 0.04)
        self.assertAlmostEqual(adjusted["adjusted_pvalues"]["B"], 0.04)
        self.assertAlmostEqual(adjusted["adjusted_pvalues"]["G"], 0.04)
        self.assertAlmostEqual(adjusted["adjusted_pvalues"]["P"], 0.04)

    def test_g_exact_dp_matches_bruteforce(self):
        weights = [2, 2, 5, 10, 10]
        observed = 9
        counts = {2: 2, 5: 1, 10: 2}
        exact = g_exact_randomization_pvalue(counts, observed)
        brute = 0
        total = 0
        for signs in itertools.product((-1, 1), repeat=len(weights)):
            total += 1
            stat = sum(w * s for w, s in zip(weights, signs))
            brute += stat >= observed
        self.assertAlmostEqual(exact, brute / total)

    def test_g_world_blocked_dp_matches_bruteforce(self):
        world_scores = [37, 13, -9, 4]
        observed = sum(world_scores)
        exact = g_world_blocked_randomization_pvalue(world_scores, observed)
        brute = 0
        total = 0
        magnitudes = [abs(score) for score in world_scores]
        for signs in itertools.product((-1, 1), repeat=len(magnitudes)):
            total += 1
            stat = sum(magnitude * sign for magnitude, sign in zip(magnitudes, signs))
            brute += stat >= observed
        self.assertAlmostEqual(exact, brute / total)

    def test_g_world_blocked_analyzer_uses_one_score_per_world(self):
        pairs = []
        for world_id, signs in ((0, (1, 1, 1, 1)), (1, (1, 0, 1, 0)), (2, (0, 1, 0, 1))):
            for weight, relevant in zip((2, 5, 10, 20), signs):
                pairs.append(
                    {
                        "world_id": world_id,
                        "weight": weight,
                        "relevant": relevant,
                        "irrelevant": 0,
                    }
                )
        result = analyze_g(
            {
                "pairs": pairs,
                "max_dose_relevant": [1, 0, 1],
                "max_dose_irrelevant": [0, 0, 0],
                "hard_gates": {"preclassified": True, "matched_corruption": True},
            }
        )
        self.assertEqual(result["analysis_mode"], "WORLD_BLOCKED_REPEATED_MEASURES")
        self.assertEqual(result["world_count"], 3)
        self.assertEqual(len(result["world_scores"]), 3)
        self.assertEqual(result["world_scores"]["0"], 37)
        self.assertEqual(result["world_scores"]["1"], 12)
        self.assertEqual(result["world_scores"]["2"], 25)

    @staticmethod
    def _pass_raw():
        wins = [(0, 1)] * 40
        ties_good = [(1, 1)] * 216
        treatment = [1] * 256
        weak = [0] * 80 + [1] * 176
        weaker = [0] * 96 + [1] * 160
        g_pairs = []
        for weight in (2, 5, 10, 20):
            g_pairs.extend(
                {"weight": weight, "relevant": 1, "irrelevant": 0}
                for _ in range(40)
            )
            g_pairs.extend(
                {"weight": weight, "relevant": 0, "irrelevant": 0}
                for _ in range(24)
            )
        return {
            "A": {
                "pairs": wins + ties_good,
                "hard_gates": {"message_nonidentifying": True, "budget_ok": True},
            },
            "B": {
                "treatment": treatment,
                "wrong_class": weak,
                "shuffled_coupling": weaker,
                "intervention_agreement": [1] * 1450 + [0] * 86,
                "hard_gates": {"grammar_independence": True, "no_translation": True},
            },
            "G": {
                "pairs": g_pairs,
                "max_dose_relevant": [1] * 64,
                "max_dose_irrelevant": [0] * 64,
                "hard_gates": {"preclassified": True, "matched_corruption": True},
            },
            "P": {
                "retained": [1] * 236 + [0] * 20,
                "baselines": {
                    "cold": [1] * 176 + [0] * 80,
                    "equal_compute_recheck": [1] * 180 + [0] * 76,
                    "verbal_rule_negative": [1] * 170 + [0] * 86,
                    "size_matched_sham": [1] * 174 + [0] * 82,
                    "wrong_class_object": [1] * 168 + [0] * 88,
                },
                "hard_gates": {
                    "zero_verifier": True,
                    "zero_search": True,
                    "label_free": True,
                    "source_distinct": True,
                    "targeted_deletion": True,
                },
                "post_deletion_accuracy": 0.69,
                "cold_accuracy": 176 / 256,
                "reacquisition_search_count": 1,
            },
        }

    def test_arm_analyzers_expose_effects_and_hard_gates(self):
        raw = self._pass_raw()
        self.assertGreaterEqual(analyze_a(raw["A"])["effect"], 0.05)
        self.assertGreaterEqual(min(analyze_b(raw["B"])["control_effects"].values()), 0.15)
        self.assertGreaterEqual(analyze_g(raw["G"])["max_dose_flip_gap"], 0.15)
        self.assertGreaterEqual(analyze_p(raw["P"])["effect"], 0.05)

    def test_matrix_pass_partial_fail_and_invalid_are_mechanical(self):
        passing = analyze_matrix(self._pass_raw())
        self.assertEqual(
            {arm: passing["arms"][arm]["verdict"] for arm in ("A", "B", "G", "P")},
            {"A": "PASS", "B": "PASS", "G": "PASS", "P": "PASS"},
        )
        self.assertEqual(passing["combined_verdict"], "PASS")

        partial_raw = self._pass_raw()
        partial_raw["A"]["pairs"] = [(0, 1)] * 10 + [(1, 1)] * 246
        partial = analyze_matrix(partial_raw)
        self.assertEqual(partial["arms"]["A"]["verdict"], "PARTIAL")
        self.assertNotEqual(partial["combined_verdict"], "PASS")

        fail_raw = self._pass_raw()
        fail_raw["P"]["post_deletion_accuracy"] = 0.90
        failed = analyze_matrix(fail_raw)
        self.assertEqual(failed["arms"]["P"]["verdict"], "FAIL")
        self.assertNotEqual(failed["combined_verdict"], "PASS")

        invalid_raw = self._pass_raw()
        invalid_raw["P"]["hard_gates"]["zero_verifier"] = False
        invalid = analyze_matrix(invalid_raw)
        self.assertEqual(invalid["arms"]["P"]["verdict"], "INVALID")
        self.assertIn(
            "P_FUTURE_VERIFIER_ACCESS",
            invalid["arms"]["P"]["validity_reason_codes"],
        )
        self.assertEqual(invalid["combined_verdict"], "INVALID")


if __name__ == "__main__":
    unittest.main()
