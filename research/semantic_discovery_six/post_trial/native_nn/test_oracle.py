import copy
import unittest

from oracle import expected, validate_case


class SampledTimeBoundaryTests(unittest.TestCase):
    def test_a_failure_at_200_is_retained_after_the_window(self):
        values = [0] * 204
        values[200] = 11
        result = expected(values)
        self.assertTrue(result[199]['past_ok'])
        self.assertFalse(result[200]['instant'])
        self.assertFalse(result[201]['past_ok'])

    def test_a_first_failure_at_201_is_outside_the_declared_window(self):
        values = [0] * 204
        values[201] = -36
        result = expected(values)
        self.assertTrue(result[200]['active'])
        self.assertFalse(result[201]['active'])
        self.assertTrue(result[201]['instant'])
        self.assertTrue(result[203]['past_ok'])

    def test_integer_one_cannot_substitute_for_a_native_boolean(self):
        case = {'id': 'wrong-type', 'values': [0], 'native': [
            {'active': 1, 'instant': True, 'past_ok': True, 'time': '0', 'step': 0, 'clock_nonnegative': True}]}
        with self.assertRaisesRegex(ValueError, 'NATIVE_BOOLEAN_TYPE_MISMATCH'):
            validate_case(case)


if __name__ == '__main__':
    unittest.main()
