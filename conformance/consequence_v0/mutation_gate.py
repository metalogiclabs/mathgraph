"""Mutation-kill gate for the actual bounded premise-audit tests.

Runs the real unittest class in fresh processes with two deliberately broken
implementations. A mutant survives if the tests still pass. The gate fails
unless both mutants are killed. No producer verdicts are trusted.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

MUTANTS={
    "accept_every_receipt": '''
import unittest
import test_real_premise_audit as m
m.bounded_audit=lambda result: {"bounded_admitted":True,
  "replay_valid":True,"current_applicability":"UNKNOWN",
  "action_authorization":"NONE",
  "contract_sha256":m.hashlib.sha256(m.CONTRACT.read_bytes()).hexdigest(),
  "policy_sha256":m.hashlib.sha256(m.POLICY.read_bytes()).hexdigest()}
suite=unittest.defaultTestLoader.loadTestsFromTestCase(m.BoundedPremiseAudit)
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
''',
    "bypass_witness_verification": '''
import unittest
import test_real_premise_audit as m
m.finite_oracle=lambda replay: {"reuse_mask":246}
suite=unittest.defaultTestLoader.loadTestsFromTestCase(m.BoundedPremiseAudit)
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
''',
}

def main():
    for name,code in MUTANTS.items():
        p=subprocess.run([sys.executable,"-c",code],cwd=HERE,
                         capture_output=True,text=True,timeout=45)
        if p.returncode==0:
            raise SystemExit("SURVIVING_MUTANT: "+name+"\n"+p.stdout+p.stderr)
        if "FAIL:" not in p.stderr:
            raise SystemExit("INCONCLUSIVE_MUTANT: "+name+"\n"+p.stdout+p.stderr)
        print("KILLED_MUTANT",name)
    print("MUTATION_GATE_PASS",len(MUTANTS),"of",len(MUTANTS))

if __name__=="__main__":
    main()
