#!/usr/bin/env python3
"""Independent receipt verifier for finite source models (never imports compiler.py)."""
from __future__ import annotations
import argparse,copy,hashlib,json,pathlib
from independent_oracle import oracle,verify_constructed_witness

def main():
    p=argparse.ArgumentParser(description='Independent finite reference checker')
    p.add_argument('--model',type=pathlib.Path,required=True)
    p.add_argument('--receipt',type=pathlib.Path,required=True)
    args=p.parse_args()
    model_bytes=args.model.read_bytes();model=json.loads(model_bytes)
    rec=json.loads(args.receipt.read_bytes())
    assert rec.get('schema')=='metalogic.consequence-to-experiment.finite-v1', 'WRONG_RECEIPT_SCHEMA'
    assert rec['input_sha256']==hashlib.sha256(model_bytes).hexdigest(), 'SOURCE_MODEL_IDENTITY_MISMATCH'
    answer=rec['result'];ref=oracle(model)
    assert answer['status']==ref['status'], 'VERDICT_MISMATCH'
    assert answer['basis_cost']==ref['basis_cost'], 'MINIMUM_COST_MISMATCH'
    assert sorted(answer['unresolved_pairs'])==sorted(ref['unresolved_pairs']), 'OBSTRUCTION_PAIR_MISMATCH'
    assert answer['closure']['transformations']==ref['transformation_count'], 'CLOSURE_MISMATCH'
    assert answer['model_name']==model['name'], 'MODEL_NAME_MISMATCH'
    verify_constructed_witness(model,answer)
    if ref['status']=='EXACT_BASIS_CONSTRUCTED':
        assert answer['diagnosis']=='COMPOSED_FROM_ALREADY_GRANTED_OPERATIONS', 'UNAUTHORIZED_PROMOTION'
    else:
        full=copy.deepcopy(model)
        full['grants']=[x['name'] for x in model['operations']+model['readouts']]
        unrestricted=oracle(full)
        expected=('MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR'
                  if unrestricted['status']=='EXACT_BASIS_CONSTRUCTED'
                  else 'NEEDS_NEW_OBSERVATION_TYPE_OR_REVISED_TARGET')
        assert answer['diagnosis']==expected, 'AUTHORITY_VS_PRIMITIVE_DIAGNOSIS_MISMATCH'
        assert answer['hypothetical_full_access_cost']==unrestricted['basis_cost'], 'HYPOTHETICAL_COST_MISMATCH'
    print('FINITE_SOURCE_MODEL_INDEPENDENT_REQUALIFICATION_PASS')
    print('SOURCE_SHA256='+hashlib.sha256(model_bytes).hexdigest())
    print('RESULT_STATUS='+answer['status'])

if __name__=='__main__':main()