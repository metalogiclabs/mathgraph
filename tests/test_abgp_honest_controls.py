import importlib.util
import inspect
import unittest
import os
import subprocess
import sys
from pathlib import Path
from fractions import Fraction

from mathgraph.abgp import arm_b
from mathgraph.abgp.arm_g import generate_g_dev_records
from mathgraph.abgp.freeze_review import audit_g_exchangeability_design
from mathgraph.abgp.runner import _b_inputs
from mathgraph.abgp.qualification import run_qualification


class HonestControlTests(unittest.TestCase):
    def exchange_api(self):
        name = 'mathgraph.abgp.exchangeability'
        self.assertIsNotNone(importlib.util.find_spec(name), 'need actual joint probability mass, not copied null outputs')
        return __import__(name, fromlist=['*'])

    def test_b_same_source_information_makes_ordinary_control_match_codec(self):
        records = arm_b.generate_b_dev_records(4)
        self.assertTrue(all(r.bisimulation_bayes_success == r.treatment_success for r in records),
                        'coarsening the comparator while source observations identify the order is not information matching')

    def test_b_representation_digest_is_stable_across_process_hash_seeds(self):
        code = "from mathgraph.abgp.arm_b import _canonical_digest; print(_canonical_digest(frozenset(str(i) for i in range(20))))"
        root = Path(__file__).resolve().parents[1]
        values = [subprocess.check_output([sys.executable, '-c', code], cwd=root,
                  env=dict(os.environ, PYTHONHASHSEED=str(seed))) for seed in (1, 2)]
        self.assertEqual(values[0], values[1])

    def test_b_oracle_takes_observation_not_hidden_truth(self):
        self.assertTrue(hasattr(arm_b, 'source_history_posterior'), 'exact finite posterior absent')
        fn = arm_b.source_history_posterior
        self.assertNotIn('world', inspect.signature(fn).parameters)
        for grammar in arm_b.grammar_families():
            world = arm_b._make_b_world('control-audit', 3)
            observation = grammar.represent(world, 'baseline')
            posterior = fn(grammar, observation)
            self.assertEqual(len(posterior), 1)
            self.assertEqual(posterior[0].base_order, grammar.infer_order(observation))

    def test_b_codec_does_not_certify_independently_generated_grammars(self):
        raw, audit = _b_inputs(arm_b.generate_b_dev_records(2))
        self.assertFalse(raw['hard_gates']['grammar_independence'])
        self.assertFalse(raw['hard_gates']['bisimulation_bound'])
        self.assertEqual(audit.get('implementation_scope'), 'EXECUTED_CODEC_CONTROL_NOT_INDEPENDENT_GRAMMAR_LEARNING')

    def test_g_matched_schedule_does_not_establish_actual_exchangeability(self):
        audit = audit_g_exchangeability_design(generate_g_dev_records(4))
        self.assertFalse(audit['joint_world_vector_exchangeability_under_null'])
        self.assertEqual(audit.get('design_argument_status'), 'ACTUAL_OUTCOME_LAW_NOT_ESTABLISHED')

    def test_equal_marginals_do_not_imply_joint_exchangeability(self):
        api = self.exchange_api()
        # Three equally probable directed edges of a cycle of two-dose vectors.
        # Both sides have the same marginals; the full paired law is asymmetric.
        law = [(((0, 0), (0, 1)), Fraction(1, 3)),
               (((0, 1), (1, 1)), Fraction(1, 3)),
               (((1, 0), (1, 0)), Fraction(1, 3))]
        audit = api.audit_joint_law(law)
        self.assertFalse(audit['exchangeable'])
        self.assertTrue(audit['separating_witnesses'])

    def test_g_exact_symmetric_nontrivial_joint_law_is_accepted(self):
        api = self.exchange_api()
        law = [(((1, 0), (0, 0)), Fraction(1, 2)),
               (((0, 1), (0, 0)), Fraction(1, 2))]
        self.assertTrue(api.audit_joint_law(law)['exchangeable'])

    def test_selection_conditioning_cannot_hide_asymmetry(self):
        api = self.exchange_api()
        # Overall outcomes balance, but outcome-dependent selection strata don't.
        law = [(((1, 0),), Fraction(1, 2)), (((0, 1),), Fraction(1, 2))]
        self.assertFalse(api.audit_joint_law(law, contexts=['keep', 'discard'])['exchangeable'])

    def test_invalid_or_incomplete_probability_support_is_rejected(self):
        api = self.exchange_api()
        with self.assertRaises(ValueError):
            api.audit_joint_law([(((1, 0),), Fraction(1, 3))])

    def test_fixture_qualification_never_authorizes_real_implementation(self):
        result = run_qualification()
        self.assertEqual(result['verdict'], 'HARNESS_QUALIFIED')
        self.assertFalse(result.get('implementation_qualified', True))
        self.assertFalse(result.get('complete_pass_power_qualified', True))
        self.assertEqual(result.get('qualification_scope'), 'STATISTICAL_AND_SYNTHETIC_FIXTURE_HARNESS_ONLY')


if __name__ == '__main__':
    unittest.main()
