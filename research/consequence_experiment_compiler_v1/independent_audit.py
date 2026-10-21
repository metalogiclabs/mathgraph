#!/usr/bin/env python3
"""Second-process audit: independently recompute casewise optimality without importing compiler."""
from __future__ import annotations
import hashlib,json,pathlib,sys
from independent_oracle import oracle,all_partitions,check_galois
from fixtures import bit_model,cyclic_model


def audit(directory:pathlib.Path):
    with (directory/'result.json').open() as f:result=json.load(f)
    with (directory/'cases.json').open() as f:cases=json.load(f)
    assert len(cases)==240
    assert result['counts']['four_state_cases']==240
    assert result['counts']['three_state_cases']==40
    assert result['galois_checks']==983040
    assert result['counts']['cost_mismatches']==0 and result['counts']['pair_mismatches']==0
    assert result['cached_single_snapshot_15_goal_batches']==16
    checks=0
    for case in cases:
        granted=['read_r']+[name for j,name in enumerate(('flip_r','zero_r','couple_h_xor_r','destroy_h')) if case['subset']&(1<<j)]
        src=bit_model(grants=granted,desired=case['part'])
        found=oracle(src)
        assert found['status']==case['status']
        assert found['basis_cost']==case['oracle_cost']==case['candidate_cost']
        assert found['transformation_count']==case['compiler_states']==case['oracle_states']
        checks+=1
    assert check_galois()==983040
    # Independently reopen second three-state domain and check all permissions/partitions.
    extra=0
    for subset in range(8):
        grants=['read_visible']+[name for j,name in enumerate(('swap_equal_protected','reset_visible','unsafe_merge')) if subset&(1<<j)]
        for part in all_partitions(3):
            x=oracle(cyclic_model(grants=grants,desired=part))
            assert x['status'] in ('EXACT_BASIS_CONSTRUCTED','UNREALIZABLE_IN_COMPLETE_DECLARED_FINITE_GRAMMAR')
            extra+=1
    assert extra==40
    body=(directory/'result.json').read_bytes();src=(directory/'cases.json').read_bytes()
    receipt={'audit':'SOURCE_INDEPENDENT_REFERENCE_REPLAY_PASS','case_count':checks,'secondary_cases':extra,
             'galois_checks':983040,'source_case_sha256':hashlib.sha256(src).hexdigest(),
             'result_sha256':hashlib.sha256(body).hexdigest(),
             'limits':['source-provided finite semantics','no new physical access','no cross-source human comparison',
                      'independent reference uses the same public model fixtures but different algorithms']}
    out=directory/'independent_audit_receipt.json';out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_REFERENCE_AUDIT_PASS',checks,extra,'GALOIS',receipt['galois_checks'])
    print('INDEPENDENT_AUDIT_SHA256',hashlib.sha256(out.read_bytes()).hexdigest())
    return receipt

if __name__=='__main__':audit(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent)