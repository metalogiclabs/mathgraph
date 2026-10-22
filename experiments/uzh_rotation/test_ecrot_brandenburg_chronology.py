import unittest
import numpy as np
from probe_ecrot_brandenburg import inspect_chronology

class ChronologyTests(unittest.TestCase):
    def test_monotonic_three_samples(self):
        d=inspect_chronology([0.,1.,2.],[0.,1.,2.],[[0,1,0]]*3)
        self.assertEqual(d["header_negative_delta_count"],0)
        self.assertTrue(d["original_parser_accepts_imu"])
        self.assertAlmostEqual(d["naive_y_integral_on_positive_intervals_turns"],2/(2*np.pi))
    def test_duplicate_timestamp_never_bridged(self):
        d=inspect_chronology([0.,1.,1.,2.],[0,1,2,3],[[0,1,0]]*4)
        self.assertEqual(d["header_duplicate_delta_count"],1)
        self.assertFalse(d["original_parser_accepts_imu"])
        self.assertAlmostEqual(d["naive_y_integral_on_positive_intervals_turns"],2/(2*np.pi))
    def test_backward_timestamp_never_integrated(self):
        d=inspect_chronology([0.,1.,0.5,1.5],[0,1,2,3],[[0,1,0]]*4)
        self.assertEqual(d["header_negative_delta_count"],1)
        self.assertFalse(d["original_parser_accepts_imu"])
        self.assertAlmostEqual(d["naive_y_integral_on_positive_intervals_turns"],2/(2*np.pi))
    def test_bad_values_fail_closed(self):
        with self.assertRaises(ValueError):
            inspect_chronology([0,1],[0,1],[[0,1,0],[0,np.nan,0]])
if __name__=="__main__":
    unittest.main()
