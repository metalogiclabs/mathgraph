"""Fail-closed bridge from real domain receipts to theorem premises.

This is an executable *premise audit*, not a Lean proof that arbitrary
adapters are sound. It reports exactly which premises are available.
"""
import hashlib
import json
import unittest
from test_stateful_campaign import invoke,finite_oracle,CONTRACT,POLICY,read

def premise_audit(result):
    evaluation=result["evaluation"]
    receipt=result.get("receipt")
    replay=receipt.get("replay") if isinstance(receipt,dict) else None
    valid=False
    if isinstance(replay,dict):
        try:
            valid=finite_oracle(replay)["reuse_mask"]==246
        except (AssertionError,ValueError,TypeError,KeyError):
            valid=False
    qualified=evaluation.get("qualification")=="QUALIFIED_BOUNDED"
    return {
        "receipt_replay_verified":valid,
        "bounded_semantics_admitted":qualified and valid,
        "source_contract_sha256":hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "trust_policy_sha256":hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "general_adapter_preservation_proof":"NOT_PROVIDED",
        "target_policy_live_support":"NOT_CHECKED",
        "freshness":evaluation.get("freshness","UNKNOWN"),
        "revocation":evaluation.get("revocation","UNKNOWN"),
        "action_authorization":evaluation.get("action_authorization","NONE"),
        "lean_premises_fully_discharged":False,
    }

class RealPremiseAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code,result=invoke()
        assert code==0
        cls.result=result
    def test_replay_but_no_unsupported_theorem_application(self):
        audit=premise_audit(self.result)
        self.assertTrue(audit["bounded_semantics_admitted"])
        self.assertFalse(audit["lean_premises_fully_discharged"])
        self.assertEqual(audit["target_policy_live_support"],"NOT_CHECKED")
    def test_producer_status_mutation_does_not_create_proof(self):
        import copy
        altered=copy.deepcopy(self.result)
        altered["evaluation"]["action_authorization"]="GRANTED"
        audit=premise_audit(altered)
        self.assertFalse(audit["lean_premises_fully_discharged"])
    def test_corrupt_witness_blocks_bounded_admission(self):
        import copy
        altered=copy.deepcopy(self.result)
        altered["receipt"]["replay"]["reuse_witness"][0]["output"]^=1
        audit=premise_audit(altered)
        self.assertFalse(audit["bounded_semantics_admitted"])
    def test_pins_are_source_derived(self):
        audit=premise_audit(self.result)
        self.assertEqual(audit["source_contract_sha256"],hashlib.sha256(CONTRACT.read_bytes()).hexdigest())
        self.assertEqual(audit["trust_policy_sha256"],hashlib.sha256(POLICY.read_bytes()).hexdigest())

if __name__=="__main__":unittest.main()
