"""Producer contracts needed by the register-only cold arithmetic interfaces."""
import unittest

MASK=2**32-1


class ColdShareTests(unittest.TestCase):
    def test_original_comparison_shift_counts_ignore_upper_code_bits(self):
        for low in range(32):
            for high in [0,0x10000,0x7fffffe0,0x80000000,0xffffffe0]:
                code=(high|low)&MASK
                cleaned=code&31
                self.assertEqual(code&31,cleaned&31)
                self.assertEqual(((code^31)+15)&31,((cleaned^31)+15)&31)
                self.assertEqual((code+2)&31,(cleaned+2)&31)

    def test_caller_must_clear_old_high_bit_before_packing_inversion(self):
        for original_code in [3,4,5,0xffff0003,0x80000005]:
            for sign in [0,1]:
                code=(original_code&31)|(sign<<31)
                for decision in [0,1]:
                    for base in [0,1,0x80000000,0xffffffff]:
                        expected=(base+(decision^sign))&MASK
                        actual=(base+(decision^(code>>31)))&MASK
                        self.assertEqual(actual,expected)
        # Deliberate falsifier: an old anchor tail's sign is not inversion.
        self.assertNotEqual(100+(0^(0x80000005>>31)),100)

    def test_positive_exp_reverse_table_offsets_equal_the_unified_offsets(self):
        for k in range(1,2048,2):
            self.assertEqual(1020-((k<<1)&1020),2*((-k)&510))
            word=(k|0xfffffe01)&MASK
            signed=word-2**32 if word>=2**31 else word
            self.assertEqual(-signed+1023,1024+((-k)&510))
        for t in range(2048):
            self.assertEqual((t<<1)&1020,2*((t|1)&510))

    def test_anchor_tail_and_implicit_request_types_preserve_their_contracts(self):
        for tail in range(-32768,32768):
            word=(tail<<14)&MASK
            signed=word-2**32 if word>=2**31 else word
            self.assertEqual(signed>>14,tail)
        for word in range(65536):
            self.assertEqual(((word<<13)&MASK)&1,0)
            self.assertEqual(((word<<14)&MASK)&1,0)
            self.assertEqual((word|1)&1,1)
            self.assertEqual((-(word|1)&MASK)&1,1)


if __name__=='__main__':unittest.main()
