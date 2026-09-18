from collections import Counter
from fractions import Fraction
import itertools
import unittest

from mathgraph.abgp.analysis import (
    exact_mcnemar_one_sided,
    g_exact_randomization_pvalue,
    g_world_blocked_randomization_pvalue,
    holm_bonferroni,
)
from mathgraph.abgp.statistical_reference import (
    reference_g_randomization,
    reference_g_world_blocked,
    reference_holm,
    reference_mcnemar,
    run_statistical_reference_audit,
)


class ABGPStatisticalReferenceTests(unittest.TestCase):
    def test_mcnemar_matches_fraction_reference_for_small_discordances(self):
        for wins in range(0, 9):
            for losses in range(0, 9 - wins):
                pairs = [(0, 1)] * wins + [(1, 0)] * losses
                observed = Fraction(exact_mcnemar_one_sided(pairs)).limit_denominator()
                self.assertEqual(observed, reference_mcnemar(wins, losses))

    def test_g_dp_matches_exhaustive_sign_reference(self):
        weight_sets = ((2,), (2, 5), (2, 2, 5), (2, 5, 10, 20))
        for weights in weight_sets:
            counts = Counter(weights)
            for observed in range(-sum(weights), sum(weights) + 1):
                scientific = Fraction(
                    g_exact_randomization_pvalue(counts, observed)
                ).limit_denominator()
                self.assertEqual(scientific, reference_g_randomization(weights, observed))

    def test_g_world_blocked_dp_matches_exhaustive_world_sign_reference(self):
        score_sets = ((2,), (2, 5), (7, -3, 4), (37, 37, 37, 37))
        for scores in score_sets:
            total = sum(scores)
            for observed in range(-sum(abs(x) for x in scores), sum(abs(x) for x in scores) + 1):
                scientific = Fraction(
                    g_world_blocked_randomization_pvalue(scores, observed)
                ).limit_denominator()
                self.assertEqual(scientific, reference_g_world_blocked(scores, observed))
            self.assertEqual(
                Fraction(g_world_blocked_randomization_pvalue(scores, total)).limit_denominator(),
                reference_g_world_blocked(scores, total),
            )

    def test_holm_matches_fraction_reference_on_small_grid(self):
        grid = (
            Fraction(0, 1),
            Fraction(1, 100),
            Fraction(1, 80),
            Fraction(1, 40),
            Fraction(1, 20),
            Fraction(1, 10),
            Fraction(1, 1),
        )
        samples = [
            {"A": a, "B": b, "G": g, "P": p}
            for a, b, g, p in itertools.product(grid, repeat=4)
        ]
        for raw in samples:
            expected = reference_holm(raw, Fraction(1, 20))
            actual = holm_bonferroni(
                {arm: float(value) for arm, value in raw.items()},
                0.05,
            )
            self.assertEqual(actual["order"], expected["order"])
            for arm in ("A", "B", "G", "P"):
                self.assertAlmostEqual(actual["adjusted_pvalues"][arm], float(expected["adjusted_pvalues"][arm]), places=15)
                self.assertEqual(actual["rejected"][arm], expected["rejected"][arm])

    def test_reference_audit_is_complete_and_green(self):
        audit = run_statistical_reference_audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertGreater(audit["mcnemar_cases"], 0)
        self.assertGreater(audit["holm_cases"], 0)
        self.assertGreater(audit["g_cases"], 0)
        self.assertGreater(audit["g_world_blocked_cases"], 0)
        self.assertLessEqual(audit["max_abs_error"], 1e-15)


if __name__ == "__main__":
    unittest.main()
