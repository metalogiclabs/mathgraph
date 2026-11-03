import copy
import unittest
from pathlib import Path
from unittest.mock import patch
import run


class AdmissionTests(unittest.TestCase):
    def test_descriptor_is_not_a_retained_argument(self):
        r = run.evaluate('attached_redirect_wrong')
        self.assertEqual(r['Verification']['execution']['calls'], [['-c']])
        self.assertEqual(r['Conclusion']['status'], 'REJECTED')
        self.assertFalse(r['Conclusion']['repair_authorized'])

    def test_spacing_quotes_and_escape_change_the_obligation(self):
        for name in ['attached_redirect', 'spaced_redirect', 'quoted_redirect',
                     'escaped_redirect', 'quoted_descriptor']:
            with self.subTest(name=name):
                self.assertEqual(run.evaluate(name)['Conclusion']['status'], 'SUPPORTED')

    def test_keyword_argument_does_not_invoke_interpreter(self):
        r = run.evaluate('argument_keyword')
        self.assertEqual(r['Verification']['execution']['calls'], [])
        self.assertEqual(r['Conclusion']['status'], 'SUPPORTED')
        self.assertEqual(run.evaluate('command_keyword')['Verification']['execution']['calls'], [['scripts/a.py']])

    def test_agreement_does_not_authorize_missing_or_disputed_requirements(self):
        for name in ['no_authority', 'disputed_requirement']:
            r = run.evaluate(name)
            self.assertEqual(r['Conclusion']['status'], 'UNKNOWN')
            self.assertEqual(r['Conclusion']['reason'], 'REQUIREMENT_NOT_ADMITTED')

    def test_arbitrary_shell_proposal_is_not_executed(self):
        proposal = copy.deepcopy(run.COHORT['cases'][0])
        proposal['command'] = 'touch /tmp/should-never-be-executed'
        with patch.object(run, 'capture', side_effect=AssertionError('execution forbidden')):
            r = run.evaluate(proposal['id'], proposal=proposal)
        self.assertEqual(r['Conclusion']['reason'], 'PROPOSAL_OUTSIDE_FROZEN_SCOPE')

    def test_changed_expectation_is_not_the_admitted_obligation(self):
        proposal = copy.deepcopy(run.COHORT['cases'][0])
        proposal['expected_calls'] = [['-c']]
        r = run.evaluate(proposal['id'], proposal=proposal)
        self.assertEqual(r['Conclusion']['status'], 'UNKNOWN')

    def test_each_dependency_change_withdraws_reuse(self):
        context = run.context()
        for field in context:
            altered = copy.deepcopy(context)
            altered[field] = 'altered'
            with self.subTest(field=field), patch.object(run, 'capture', side_effect=AssertionError('stale reuse')):
                r = run.evaluate('attached_redirect', required_context=altered)
            self.assertEqual(r['Conclusion']['reason'], 'CONTEXT_CHANGED')

    def test_reject_all_oracle_fails_positive_control(self):
        with patch.object(run, 'capture', return_value={'status':'OK','calls':[],'exit':0}):
            r = run.evaluate('argument_keyword')
        self.assertEqual(r['Conclusion']['reason'], 'REFERENCE_CONTROL_FAILED')

    def test_always_invoke_oracle_fails_negative_control(self):
        with patch.object(run, 'capture', return_value={'status':'OK','calls':[['guard.py']],'exit':0}):
            r = run.evaluate('attached_redirect')
        self.assertEqual(r['Conclusion']['reason'], 'REFERENCE_CONTROL_FAILED')

    def test_timeout_is_unknown_not_counterevidence(self):
        with patch.object(run.subprocess, 'run', side_effect=run.subprocess.TimeoutExpired('bash', 2)):
            obs = run.capture('python3 guard.py')
        self.assertEqual(obs['status'], 'TIMEOUT')

    def test_crash_and_nonzero_are_distinct(self):
        for code, status in [(-9, 'CRASH'), (2, 'ERROR')]:
            with patch.object(run.subprocess, 'run', return_value=run.subprocess.CompletedProcess('bash', code, b'', b'diagnostic')):
                self.assertEqual(run.capture('python3 guard.py')['status'], status)

    def test_nonrepeatable_observation_is_unknown(self):
        ok = lambda calls: {'status':'OK','calls':calls,'exit':0}
        observations = [ok([['guard.py']]), ok([]), ok([['-c']]), ok([])]
        with patch.object(run, 'capture', side_effect=observations):
            r = run.evaluate('attached_redirect')
        self.assertEqual(r['Conclusion']['reason'], 'REFERENCE_NOT_REPEATABLE')

    def test_results_keep_the_six_roles_and_no_repair_authorization(self):
        r = run.evaluate('attached_redirect')
        self.assertEqual(set(r), {'Subject','Obligation','Relation','Verification','Conclusion','Dependencies'})
        self.assertFalse(r['Conclusion']['repair_authorized'])

    def test_missing_reference_binary_yields_unknown_receipt(self):
        with patch.object(run, 'BASH', Path('/definitely/missing/mathgraph-bash')):
            r = run.evaluate('attached_redirect')
        self.assertEqual(r['Conclusion']['status'], 'UNKNOWN')
        self.assertEqual(r['Conclusion']['reason'], 'REFERENCE_IDENTITY_UNAVAILABLE')
        self.assertIsNone(r['Dependencies']['bash_sha256'])


if __name__ == '__main__':
    unittest.main()
