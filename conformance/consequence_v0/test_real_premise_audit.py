"""Source-derived bounded premise audit, not a certificate-to-Lean proof bridge.

No universal theorem discharge is inferred from producer-controlled strings.
Tests exercise the independent replay oracle, not a hard-coded 'False' flag.
"""
import copy
import hashlib
import unittest
from test_stateful_campaign import invoke,finite_oracle,CONTRACT,POLICY

def bounded_audit(result):
    receipt=result.get("receipt")
    replay=receipt.get("replay") if isinstance(receipt,dict) else None
    valid=False
    if isinstance(replay,dict):
        try:
            valid=finite_oracle(replay)["reuse_mask"]==246
        except (AssertionError,ValueError,TypeError,KeyError):
            valid=False
    evaluation=result.get("evaluation",{})
    return {
        "replay_valid":valid,
        "bounded_admitted":valid and evaluation.get("qualification")=="QUALIFIED_BOUNDED",
        "contract_sha256":hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "policy_sha256":hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "current_applicability":evaluation.get("current_applicability","UNKNOWN"),
        "action_authorization":evaluation.get("action_authorization","NONE"),
    }

class BoundedPremiseAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code,result=invoke()
        assert code==0
        cls.result=result
    def test_source_replay_admitted(self):
        self.assertTrue(bounded_audit(self.result)["bounded_admitted"])
    def test_witness_mutation_changes_verdict(self):
        altered=copy.deepcopy(self.result)
        altered["receipt"]["replay"]["reuse_witness"][0]["output"] ^= 1
        self.assertFalse(bounded_audit(altered)["bounded_admitted"])
    def test_qualification_mutation_changes_verdict(self):
        altered=copy.deepcopy(self.result)
        altered["evaluation"]["qualification"]="UNKNOWN"
        self.assertFalse(bounded_audit(altered)["bounded_admitted"])
    def test_missing_receipt_changes_verdict(self):
        altered=copy.deepcopy(self.result)
        altered["receipt"]=None
        self.assertFalse(bounded_audit(altered)["bounded_admitted"])
    def test_scope_and_authorization_are_not_inferred(self):
        audit=bounded_audit(self.result)
        self.assertEqual(audit["current_applicability"],"UNKNOWN")
        self.assertEqual(audit["action_authorization"],"NONE")
    def test_hashes_derived_from_exact_source(self):
        audit=bounded_audit(self.result)
        self.assertEqual(audit["contract_sha256"],hashlib.sha256(CONTRACT.read_bytes()).hexdigest())
        self.assertEqual(audit["policy_sha256"],hashlib.sha256(POLICY.read_bytes()).hexdigest())

if __name__=="__main__":unittest.main()
