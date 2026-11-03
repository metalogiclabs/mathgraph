import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('assess', Path(__file__).with_name('assess.py'))
mod = importlib.util.module_from_spec(spec)
if spec.loader and spec.origin and Path(spec.origin).exists():
    spec.loader.exec_module(mod)

def arm(**kw):
    return {'complete': True, 'contract': 'PASS', 'behavior': 'PASS', 'generation':'NOT_REQUIRED', 'consumer_reached':True, 'unapproved_axioms':[], 'gate_exit':0, 'build_exit':0, 'hashes':{'Subject.lean':'a'*64}, **kw}

class EvidenceAdmission(unittest.TestCase):
    def test_incomplete_head_never_promotes_raw_failures(self):
        row = arm(complete=False, contract='FAIL', behavior='FAIL')
        self.assertEqual(getattr(mod, 'compare', lambda *_: None)(arm(), row), 'UNKNOWN')

    def test_inherited_is_not_introduced(self):
        row = arm(contract='FAIL', behavior='FAIL')
        self.assertEqual(getattr(mod, 'compare', lambda *_: None)(row, row), 'INHERITED_FAILURE')

    def test_same_proposition_alternative_proof_is_accepted(self):
        row = arm()
        self.assertEqual(getattr(mod, 'compare', lambda *_: None)(row, row), 'BOUNDED_PASS')

    def test_changed_contract_is_not_permission_to_weaken_it(self):
        self.assertEqual(getattr(mod, 'compare', lambda *_: None)({'complete': True}, {'complete': True, 'contract_changed': True}), 'OWNER_REVIEW_REQUIRED')

    def test_unapproved_axiom_is_distinct_from_type_failure(self):
        self.assertEqual(getattr(mod, 'issues', lambda *_: None)({'contract': 'PASS', 'unapproved_axioms': ['Subject.oracle']}), ['ASSUMPTION_POLICY_FAILURE'])

    def test_changed_assumption_cannot_be_labelled_inherited(self):
        base = arm(unapproved_axioms=['Subject.old'])
        head = arm(unapproved_axioms=['Subject.new'])
        self.assertEqual(mod.compare(base,head), 'FAILURE_ON_BOTH_REVISIONS')

    def test_sparse_complete_flag_does_not_supply_evidence(self):
        self.assertEqual(mod.compare({'complete':True},{'complete':True}), 'UNKNOWN')

    def test_malformed_native_fields_fail_closed(self):
        for bad in [arm(hashes={'Subject.lean':None}),arm(build_exit=False)]:
            self.assertEqual(mod.compare(arm(),bad),'UNKNOWN')

    def test_missing_build_consumer_is_not_credited_by_independent_replay(self):
        self.assertEqual(getattr(mod, 'issues', lambda *_: None)({'contract': 'PASS', 'consumer_reached': False}), ['REQUIRED_CONSUMER_NOT_BUILT'])

if __name__ == '__main__': unittest.main()
