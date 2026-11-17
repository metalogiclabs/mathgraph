"""A missing consequential question is selected, not provided by hand."""

import unittest

from research.fret_authority_pair_v0.witness import find_future_distinction


class BoundedQuestionDiscovery(unittest.TestCase):
    def test_finds_minimum_one_pulse_trace_and_asks_for_t0_semantics(self):
        result = find_future_distinction((0, 7), (2, 7), horizon=8,
                                         trigger="BOOST", response="COAST")
        self.assertIsNotNone(result)
        self.assertEqual(result.response_trace, (1, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual((result.first_verdict, result.second_verdict), (True, False))
        self.assertEqual(result.trials, 2)  # zero response first, one pulse at t0 second
        self.assertEqual(result.question,
                         "Does COAST at offset 0 after BOOST count as satisfying the requirement?")

    def test_equivalent_windows_have_no_bounded_separating_trace(self):
        self.assertIsNone(find_future_distinction((0, 7), (0, 7), horizon=8,
                                                  trigger="BOOST", response="COAST"))

    def test_short_online_prefix_cannot_be_mistaken_for_complete_window(self):
        with self.assertRaisesRegex(ValueError, "full.*window"):
            find_future_distinction((0, 7), (2, 7), horizon=2,
                                    trigger="BOOST", response="COAST")

    def test_unbounded_or_invalid_search_space_is_rejected(self):
        for bound in (0, -1, 20):
            with self.subTest(bound=bound):
                with self.assertRaises(ValueError):
                    find_future_distinction((0, 7), (2, 7), horizon=bound,
                                            trigger="BOOST", response="COAST")

    def test_every_eight_tick_future_window_pair_against_set_oracle(self):
        # 36 intervals x 36 intervals = 1296 independently checked pairs.
        # The set-theoretic symmetric difference is an independent reference.
        windows = [(low, high) for low in range(8) for high in range(low, 8)]
        for first in windows:
            for second in windows:
                with self.subTest(first=first, second=second):
                    left = set(range(first[0], first[1] + 1))
                    right = set(range(second[0], second[1] + 1))
                    difference = left ^ right
                    witness = find_future_distinction(first, second, horizon=8,
                                                     trigger="BOOST", response="COAST")
                    if not difference:
                        self.assertIsNone(witness)
                        continue
                    offset = min(difference)
                    self.assertIsNotNone(witness)
                    self.assertEqual(tuple(i for i, bit in enumerate(witness.response_trace)
                                           if bit), (offset,))
                    self.assertEqual(witness.trials, offset + 2)
                    self.assertEqual((witness.first_verdict, witness.second_verdict),
                                     (offset in left, offset in right))


if __name__ == "__main__":
    unittest.main()
