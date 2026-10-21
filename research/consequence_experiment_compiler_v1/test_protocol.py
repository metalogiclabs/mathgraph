#!/usr/bin/env python3
"""Frozen adversarial controls; candidate vs independently authored exact oracle."""
from __future__ import annotations
from itertools import combinations
import copy,hashlib,json,time
from pathlib import Path
import compiler
from independent_oracle import oracle,all_partitions,check_galois,verify_constructed_witness
from fixtures import bit_model,cyclic_model


def run():
    counts={'four_state_cases':0,'three_state_cases':0,'constructed':0,'obstructed':0,'cost_mismatches':0,
            'pair_mismatches':0,'witness_mismatches':0,'source_primitive_invention':0}
    cases=[]
    for subset in range(16):
        granted=['read_r']+[name for j,name in enumerate(('flip_r','zero_r','couple_h_xor_r','destroy_h')) if subset&(1<<j)]
        for part in all_partitions(4):
            model=bit_model(grants=granted,desired=part)
            t0=time.perf_counter_ns();answer=compiler.compile_experiment(model);t1=time.perf_counter_ns()
            original=oracle(model);t2=time.perf_counter_ns()
            counts['four_state_cases']+=1
            if answer['status']=='EXACT_BASIS_CONSTRUCTED':counts['constructed']+=1
            else:counts['obstructed']+=1
            if answer['basis_cost']!=original['basis_cost'] or answer['status']!=original['status']:
                counts['cost_mismatches']+=1
                raise AssertionError({'model':model,'compiler':answer,'oracle':original})
            if sorted(answer['unresolved_pairs'])!=sorted(original['unresolved_pairs']):
                counts['pair_mismatches']+=1;raise AssertionError('Independent obstruction mismatch')
            verify_constructed_witness(model,answer)
            if answer['status']!='EXACT_BASIS_CONSTRUCTED':
                # Verify no semantic gap between all allowed transformations and admitted observed profiles.
                assert answer['closure']['transformations']==original['transformation_count']
            cases.append({'domain':'4','subset':subset,'part':part,'status':answer['status'],
                          'candidate_cost':answer['basis_cost'],'oracle_cost':original['basis_cost'],
                          'candidate_us':(t1-t0)//1000,'oracle_us':(t2-t1)//1000,
                          'compiler_states':answer['closure']['transformations'],
                          'oracle_states':original['transformation_count']})
    for subset in range(8):
        granted=['read_visible']+[name for j,name in enumerate(('swap_equal_protected','reset_visible','unsafe_merge')) if subset&(1<<j)]
        for part in all_partitions(3):
            model=cyclic_model(grants=granted,desired=part)
            answer=compiler.compile_experiment(model);original=oracle(model)
            counts['three_state_cases']+=1
            assert answer['status']==original['status'] and answer['basis_cost']==original['basis_cost']
            assert sorted(answer['unresolved_pairs'])==sorted(original['unresolved_pairs'])
            assert answer['closure']['transformations']==original['transformation_count']
            verify_constructed_witness(model,answer)
    all_granted=compiler.compile_experiment(bit_model())
    assert all_granted['status']=='EXACT_BASIS_CONSTRUCTED' and all_granted['basis_cost']==4,all_granted
    assert all_granted['basis'][0]['program']==['couple_h_xor_r','read_r'],all_granted
    no_couple=compiler.compile_experiment(bit_model(grants=['read_r','flip_r','zero_r','destroy_h']))
    assert no_couple['diagnosis']=='MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR',no_couple
    absent=bit_model(grants=['read_r','flip_r','zero_r','destroy_h']);absent['operations']=[x for x in absent['operations'] if x['name']!='couple_h_xor_r']
    new_primitive=compiler.compile_experiment(absent)
    assert new_primitive['diagnosis']=='NEEDS_NEW_OBSERVATION_TYPE_OR_REVISED_TARGET',new_primitive
    # Having permission for the destructive primitive does not make it a safe constructor.
    destructive=compiler.compile_experiment(bit_model(grants=['read_r','destroy_h']))
    assert destructive['diagnosis']=='MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR'
    raw=next(op for op in bit_model()['operations'] if op['name']=='destroy_h')['image']
    assert raw[0]==0 and raw[2]==1 and raw[3]==1
    assert bit_model()['readouts'][0]['values'][raw[0]] != bit_model()['readouts'][0]['values'][raw[2]]
    assert bit_model()['protected'][raw[2]] != bit_model()['protected'][2]
    # A future that ALSO protects record state invalidates the coupling; current h-only proof is not universal.
    full_future=bit_model()
    full_future['protected']=[0,1,2,3]
    future=compiler.compile_experiment(full_future)
    assert future['status']=='UNREALIZABLE_IN_COMPLETE_DECLARED_FINITE_GRAMMAR'
    assert future['diagnosis']=='NEEDS_NEW_OBSERVATION_TYPE_OR_REVISED_TARGET'
    # Cost-optimality and alternative instrument fallback, rather than a mistaken fixed-mode selection.
    alternative=bit_model()
    alternative['operations'].append({'name':'copy_h_into_r','image':[0,0,3,3],'cost':4})
    alternative['grants'].append('copy_h_into_r')
    assert compiler.compile_experiment(alternative)['basis_cost']==4
    alternative['grants'].remove('couple_h_xor_r')
    fallback=compiler.compile_experiment(alternative)
    assert fallback['basis_cost']==5 and fallback['basis'][0]['program']==['copy_h_into_r','read_r'],fallback
    # Multiple original readouts use their JOINT observation kernel, no hardcoded first-column shortcut.
    dual=bit_model()
    dual['readouts'].append({'name':'read_h','values':[0,0,1,1],'cost':4})
    dual['grants'].append('read_h')
    dual['base_readouts'].append('read_h')
    assert compiler.compile_experiment(dual)['basis_cost']==0
    assert oracle(dual)['basis_cost']==0
    verify_constructed_witness(dual,compiler.compile_experiment(dual))
    # Target already achieved by original known readout requires no new work.
    none=compiler.compile_experiment(bit_model(desired=[0,1,0,1]))
    assert none['basis']==[] and none['basis_cost']==0,none
    # The claimed obstruction must NOT be turned into a universal claim if the monoid cap is exceeded.
    insufficient=bit_model();insufficient['max_monoid']=1
    try:compiler.compile_experiment(insufficient)
    except OverflowError as e:assert 'RESOURCE_BOUND' in str(e)
    else:raise AssertionError('Resource exhaustion was incorrectly interpreted as impossibility')
    # Permission and evidence remain separate. Two alternative supports are not disjunctive when
    # both depend on the same operator grant; unauthorized plans do not acquire warrant.
    def claim(active):
        chains=[{'grant:couple','source:A','native:A'}, {'grant:couple','source:B','native:B'}]
        return 'DIST' if any(c <= active for c in chains) else 'UNKNOWN'
    tokens={'grant:couple','source:A','native:A','source:B','native:B'}
    assert claim(tokens)=='DIST'
    assert claim(tokens-{'source:A'})=='DIST'
    assert claim(tokens-{'source:A','source:B'})=='UNKNOWN'
    assert claim(tokens-{'grant:couple'})=='UNKNOWN'
    assert claim(tokens)==claim(set(tokens))
    # Reuse one exact fixed-snapshot observation algebra across ALL 15 target partitions.
    # No cached data crosses a different authority/grant snapshot.
    for subset in range(16):
        granted=['read_r']+[name for j,name in enumerate(('flip_r','zero_r','couple_h_xor_r','destroy_h')) if subset&(1<<j)]
        model=bit_model(grants=granted)
        goals=list(all_partitions(4))
        batch=compiler.compile_many(model,goals)
        assert batch['snapshot_closure_calculations']==1
        assert batch['hypothetical_full_access_closure_calculations']<=1
        for goal,got in zip(goals,batch['results']):
            cold=compiler.compile_experiment(bit_model(grants=granted,desired=goal))
            for field in ('status','basis_cost','basis','unresolved_pairs','diagnosis'):
                assert got[field]==cold[field],(subset,goal,field,got,cold)
    # Denying an operation is a new snapshot, not a cache lookup into the old one.
    cold_denied=compiler.compile_experiment(bit_model(grants=['read_r','flip_r','zero_r','destroy_h']))
    assert cold_denied['diagnosis']=='MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR'
    result={
        'status':'BOUNDED_FINITE_COMPILER_REPLAY_PASS',
        'scope':'supplied complete finite state and operation/readout tables; stagewise protected safety; no new primitive invention',
        'counts':counts, 'galois_checks':check_galois(),
        'cached_single_snapshot_15_goal_batches':16,
        'cached_snapshot_computations_per_batch':1,
        'main_witness':{'program':all_granted['basis'][0]['program'],'cost':all_granted['basis_cost']},
        'permission_withdrawal_status':no_couple['diagnosis'],
        'absent_primitive_status':new_primitive['diagnosis'],
        'destructive_control':destructive['diagnosis'],
        'safe_alternative_restoration':fallback['basis'][0]['program'],
        'retained_claim_support':'ALT_SUPPORT_SURVIVES_SINGLE_WITHDRAWAL_AND_FAILS_BOTH_OR_PERMISSION',
        'comparator':'independently implemented closure + Bellman-Ford paths + exhaustive experiment subset; exact minimum cost TIE',
        'stop':['No empirical discovery','No autonomous primitive invention','No statistically measured biological advantage',
                'No extension to stochastic/infinite/partial physical domains','No live signed CLC kernel here'],
        'runtime_metric_scope':'candidate and baseline per-case process times, Python implementation/runtime dependent; excludes native adapter and lab access costs'
    }
    out=Path(__file__).with_name('result.json')
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    samples=Path(__file__).with_name('cases.json')
    samples.write_text(json.dumps(cases,sort_keys=True,indent=2)+'\n')
    print('PROTECTED_BASIS_COMPILER_ORACLE_PASS',counts['four_state_cases'],counts['three_state_cases'],'GALOIS',result['galois_checks'])
    print('PERMISSION_OBSTRUCTION_SEPARATION_PASS')
    print('INDEPENDENT_COST_OPTIMALITY_TIE')
    print('RESULT_SHA256',hashlib.sha256(out.read_bytes()).hexdigest())
    return result

if __name__=='__main__':run()