import unittest

from fused_quadratic import certificate


class FusedQuadraticTests(unittest.TestCase):
    def test_guard_preserves_the_full_word_quotient(self):
        mask = 2**32 - 1
        for q in (0, 1, 2**24 - 1):
            for residue in range(21, 240):
                b = q * 256 + residue
                for delta in range(-2, 17):
                    a = (b + delta) & mask
                    self.assertEqual(a >> 8, b >> 8)
                    self.assertGreaterEqual(a & 255, 19)

    def test_an_overbroad_guard_has_a_counterexample(self):
        b = 0
        a = (b - 2) & (2**32 - 1)
        self.assertNotEqual(a >> 8, b >> 8)

    def test_positive_bias_needs_only_a_lower_bound(self):
        mask = 2**32 - 1
        for q in (0, 1, 2**24 - 1):
            for residue in range(37, 256):
                b = q * 256 + residue
                for delta in range(-18, 1):
                    a = (b + delta) & mask
                    self.assertEqual(a >> 8, b >> 8)
                    self.assertGreaterEqual(a & 255, 19)

    def test_product_range_rejects_a_bad_table(self):
        with self.assertRaisesRegex(ValueError, 'unsigned range'):
            certificate([[0, 65535, 65535]])


if __name__ == '__main__':
    unittest.main()
