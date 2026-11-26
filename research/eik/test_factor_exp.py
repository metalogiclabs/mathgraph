import unittest
from factor_exp import coordinate, tables


def word_of_scaled(value, base):
    shift = 7 if value < 2**31 else 8
    q, rem = divmod(value, 1 << shift)
    half = 1 << (shift-1)
    rounded = q+(rem>half or (rem==half and q&1))
    return base-(0x800000 if shift==7 else 0)+rounded


class FactorExpTests(unittest.TestCase):
    def test_coordinate_retains_every_input_fraction_bit_in_representative_strata(self):
        for e in range(124,130):
            for frac in list(range(4096))+[(i<<11)+j for i in range(4096) for j in (0,1,1023,2047)]:
                w=0x80000000+(e<<23)+frac
                self.assertEqual(coordinate(w),(0x800000+frac)<<(e-122))

    def test_biased_guard_preserves_rounding_across_the_binade_boundary(self):
        base=126<<23
        centers=[2**31-1024,2**31,2**31+1024,0xe0000000]
        for center in centers:
            for biased in range(center-1024,center+1024):
                shift=7 if biased<2**31 else 8
                q=biased+(1<<(shift-1))
                mask=(1<<shift)-8
                if not q&mask:
                    continue
                got=base-(0x800000 if shift==7 else 0)+(q>>shift)
                for error in range(8):
                    self.assertEqual(got,word_of_scaled(biased-error,base))

    def test_residual_product_and_factor_tables_fit_the_declared_words(self):
        self.assertLess(65535*65535,2**32)
        for a,b in [(3,12),(5,13)]:
            large,small=tables(a,b)
            self.assertEqual(len(large),8<<a)
            self.assertEqual(len(small),1<<(b-a))
            self.assertEqual(small[0],2**32-1)
            self.assertTrue(all(0<v<2**32 for v in small))
            self.assertTrue(all(small[i]>=small[i+1] for i in range(len(small)-1)))


if __name__=='__main__':
    unittest.main()
