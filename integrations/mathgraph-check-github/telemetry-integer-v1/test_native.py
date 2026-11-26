import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from corpus import Case, cases, same_value
from native import load_accessor, observe, UnavailableConfigParser


def source(expression):
    return ('from openc3.config.config_parser import ConfigParser\n'
            'class Accessor:\n @classmethod\n def convert_to_type(cls, value, item):\n'
            f'  return {expression}\n')


class NumericContractTests(unittest.TestCase):
    def test_contract_has_stable_distinct_cases_and_all_families(self):
        roster = cases()
        self.assertEqual(len(roster), 108)
        self.assertEqual(len({case.id for case in roster}), 108)
        self.assertEqual({case.family for case in roster},
                         {'integer_identity', 'compatibility', 'invalid_input'})

    def test_independent_identity_rejects_float_bool_and_list_type_substitution(self):
        self.assertFalse(same_value(float(2**53+1), 2**53+1))
        self.assertFalse(same_value(1.0, 1))
        self.assertFalse(same_value(True, 1))
        self.assertFalse(same_value((1,), [1]))
        self.assertTrue(same_value([2**64-1], [2**64-1]))

    def test_float_intermediate_exposes_the_known_precision_class(self):
        convert, _ = load_accessor(source('int(float(value))'))
        item = SimpleNamespace(data_type='INT', array_size=None)
        self.assertNotEqual(convert(2**53+1, item), 2**53+1)

    def test_projection_refuses_the_excluded_dependency(self):
        convert, _ = load_accessor(source('ConfigParser.handle_true_false(value)'))
        with self.assertRaisesRegex(RuntimeError, 'OUTSIDE_PROFILE'):
            convert('TRUE', SimpleNamespace())

    def test_interface_drift_does_not_receive_an_inferred_adapter(self):
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED'):
            load_accessor(source('value').replace('convert_to_type', 'other'))
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED'):
            load_accessor(source('value').replace('ConfigParser\n', 'ConfigParser as Other\n'))

    def test_unexpected_runtime_failure_is_not_a_semantic_discrepancy(self):
        def broken(*_): raise OSError('apparatus unavailable')
        with self.assertRaisesRegex(RuntimeError, 'UNEXPECTED_NATIVE_EXCEPTION'):
            observe(broken)

    def test_mutating_input_cannot_change_the_expected_array(self):
        original = [2**53+1]
        case = Case('alias-control', 'integer_identity', 'INT', True, original, original)
        def mutate(value, _item):
            value[0] = 0
            return value
        with patch('native.cases', return_value=[case]):
            row = observe(mutate)[0]
        self.assertFalse(row['passed'])
        self.assertEqual(original, [2**53+1])
        self.assertEqual(row['expected_repr'], '[9007199254740993]')


if __name__ == '__main__': unittest.main()
