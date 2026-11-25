"""Integration checks for preserving author equations and qualification predicates."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('nn_native_prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class ProjectionTests(unittest.TestCase):
    def test_compiler_projection_preserves_range_predicate_and_equation(self):
        node = 'node n(N:int) returns(y:int;);\nlet\nassert ((-2147483648 <= N) and (N <= 2147483647));\ny = 0 -> pre y + N;\ntel'
        projected, bounds = prepare.project(node)
        self.assertEqual(bounds, ['((-2147483648 <= N) and (N <= 2147483647))'])
        self.assertIn('assume "original_range_0" ' + bounds[0] + ';', projected)
        self.assertIn('y = 0 -> pre y + N;', projected)
        self.assertNotIn('\nassert ', projected)

    def test_a_node_without_range_assumptions_is_byte_identical(self):
        node = 'node n(x:bool) returns(y:bool;);\nlet\ny = not x;\ntel'
        self.assertEqual(prepare.project(node), (node, []))

    def test_native_monitor_exposes_verdicts_as_outputs(self):
        # Kind 2 omits proved properties from generated code. Verdicts must be
        # observable outputs rather than proof-only annotations.
        self.assertIn('active:bool; instant:bool; past_ok:bool;', prepare.HARNESS)
        self.assertIn('past_ok = instant and (true -> pre past_ok);', prepare.HARNESS)


if __name__ == '__main__':
    unittest.main()
