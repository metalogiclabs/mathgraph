"""Arithmetic contract and falsifiers for the packed numerical cell proposal."""
import unittest

from synthesize_uniform_exp import pack_interval


MASK = 2**32-1


class PackedResidueTests(unittest.TestCase):
    def test_every_admitted_residue_preserves_the_guarded_quotient(self):
        # Enumerate all possible residues within the declared error interval.
        # This tests the integer packing rule independently of the fit heuristic.
        admitted = 0
        for cubic in range(-256, 256):
            result = pack_interval(-256000+37, -256000+26, cubic, 0, 65536)
            if result is None:
                continue
            packed, base, threshold = result
            self.assertEqual(packed & 255, cubic & 255)
            difference = packed-256*base
            self.assertGreaterEqual(difference, -256000+37)
            for t in range(256+threshold+1):
                q = 256*min(base, 256)+t
                y = base-min(base, 256)
                if ((q << 24) & MASK) > packed:
                    self.assertEqual(base-(q >> 8), y)
            admitted += 1
        self.assertGreater(admitted, 0)

    def test_guard_cannot_cover_an_unbounded_approximation_error(self):
        packed = 1 << 24
        y, base, q = 100, 100, 511
        self.assertGreater((q << 24) & MASK, packed)
        self.assertNotEqual(base-(q >> 8), y)

    def test_a_declined_cell_does_not_choose_the_rounding_bit(self):
        # Same low-byte guard result admits two different true quotients.
        packed, q = 20 << 24, 256000+5
        self.assertLessEqual((q << 24) & MASK, packed)
        y0 = 123456
        base = y0+(q >> 8)
        difference = packed-256*base
        p = q-packed
        # Both hypothetical oracle outputs satisfy the exact error contract.
        # Therefore a caller cannot derive the rounding bit from this guard.
        for oracle_y in (y0, y0+1):
            transformed_error = difference+p+256*oracle_y
            self.assertGreaterEqual(transformed_error, 0)
            self.assertLessEqual(transformed_error, 256+20)
        self.assertNotEqual(base-(q >> 8), y0+1)
        self.assertNotEqual(base-(q >> 8)+1, y0)

    def test_signed_halfword_repacking_preserves_output_and_guard(self):
        for cubic in (-32768, -1, 0, 1, 32767):
            packed = (11 << 24) | (cubic & 0xffffff)
            narrow = (11 << 24) | (cubic & 65535)
            delta = narrow-packed
            self.assertEqual(delta % 256, 0)
            for p in range(0, 4096):
                old_q, new_q = packed+p, narrow+p
                self.assertEqual(((old_q << 24) & MASK) > packed,
                                 ((new_q << 24) & MASK) > narrow)
                self.assertEqual(123456-(old_q >> 8),
                                 123456+delta//256-(new_q >> 8))

    def test_unrepresentable_guard_and_wrapped_products_are_rejected(self):
        self.assertIsNone(pack_interval(0, -256, 0, 0, 1))
        self.assertIsNone(pack_interval(-256000, -256000+20, 0, -1, 0))
        self.assertIsNone(pack_interval(-256000, -256000+20, 0, 0, 2**32))
        self.assertIsNone(pack_interval(-256000, -256000+20, 2**23, 0, 1))


if __name__ == '__main__':
    unittest.main()
