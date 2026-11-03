import unittest,importlib.util,copy
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('leading_admission',ROOT/'admission.py')
admission=importlib.util.module_from_spec(spec)
try:spec.loader.exec_module(admission)
except FileNotFoundError:admission=None

class AdmissionTests(unittest.TestCase):
    def test_frozen_leading_redirect_and_filename_expectations_are_reference_bound(self):
        self.assertIsNotNone(admission,'leading-redirection admission adapter is missing')
        for p in admission.POLICY['proposals']:
            with self.subTest(p['id']):self.assertEqual(admission.bind(p,admission.POLICY['subject']['sha256'])['status'],'ADMITTED')
    def test_wrong_subject_and_true_shortcut_cannot_authorize(self):
        self.assertIsNotNone(admission,'leading-redirection admission adapter is missing')
        p=copy.deepcopy(admission.POLICY['proposals'][0]);self.assertEqual(admission.bind(p,'0'*64)['status'],'UNKNOWN')
        p['expression']='true';self.assertEqual(admission.bind(p,admission.POLICY['subject']['sha256'])['status'],'UNKNOWN')
    def test_unfrozen_commands_cannot_run(self):
        self.assertIsNotNone(admission,'leading-redirection admission adapter is missing')
        self.assertEqual(admission.reference.capture('python3 unreviewed.py')['status'],'UNSUPPORTED')
    def test_operator_scope_is_not_customer_approval(self):
        self.assertIsNotNone(admission,'leading-redirection admission adapter is missing')
        for c in admission.reference.COHORT['cases']:self.assertEqual(c['authority']['customer_approval'],'UNKNOWN')
    def test_frozen_but_weak_expression_and_wrong_typed_value_remain_unadmitted(self):
        self.assertIsNotNone(admission)
        for field,value,status in [('expression','true','UNKNOWN'),('expected',[],'REJECTED')]:
            policy=copy.deepcopy(admission.POLICY);p=policy['proposals'][0];p[field]=value
            with self.subTest(field=field),patch.object(admission.base,'POLICY',policy):
                self.assertEqual(admission.bind(p,policy['subject']['sha256'])['status'],status)
    def test_missing_or_disputed_authority_cannot_be_promoted_by_matching_execution(self):
        for state in ['HYPOTHESIS','DISPUTED']:
            cohort=copy.deepcopy(admission.reference.COHORT);cohort['cases'][0]['authority']['state']=state
            with self.subTest(state=state),patch.object(admission.reference.base,'COHORT',cohort):
                self.assertEqual(admission.bind(admission.POLICY['proposals'][0],admission.POLICY['subject']['sha256'])['status'],'UNKNOWN')
    def test_no_invocation_or_always_invocation_oracles_fail_controls(self):
        for calls in [[],[['guard.py']]]:
            with self.subTest(calls=calls),patch.object(admission.reference.base,'capture',return_value={'status':'OK','calls':calls,'exit':0}):
                self.assertEqual(admission.bind(admission.POLICY['proposals'][0],admission.POLICY['subject']['sha256'])['status'],'UNKNOWN')

if __name__=='__main__':unittest.main()
