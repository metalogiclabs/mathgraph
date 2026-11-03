import unittest,importlib.util,copy
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

if __name__=='__main__':unittest.main()
