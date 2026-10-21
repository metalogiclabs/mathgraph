"""Fail-closed pre-exposure readiness. Does NOT run protected targets."""
import json
import pathlib
import sys

REQUIRED = ("candidate_source_sha256", "baseline_source_sha256",
            "independent_evaluator_source_sha256", "second_generation_seal_sha256",
            "resource_budget_sha256", "permission_contract_sha256",
            "measurement_protocol_sha256", "source_native_contract_sha256")
def evaluate(lock):
    missing=[name for name in REQUIRED if not isinstance(lock.get(name),str)
             or len(lock[name])!=64 or any(c not in "0123456789abcdef" for c in lock[name])]
    if missing:
        return {"status":"BLOCKED_PRELOCK", "missing":missing}
    return {"status":"LOCK_FIELDS_PRESENT_NOT_AUTHENTICATED",
            "warning":"Digest syntax is not evaluator independence, source authorization, or scientific qualification"}

if __name__=="__main__":
    p=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else None
    lock=json.loads(p.read_text()) if p else {}
    result=evaluate(lock)
    print(json.dumps(result,sort_keys=True))
    # Empty-source fixture must be blocked. This is the expected correct gate.
    sys.exit(0 if result["status"]=="BLOCKED_PRELOCK" else 2)
