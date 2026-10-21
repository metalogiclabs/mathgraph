#!/usr/bin/env python3
"""Additional independent deterministically seeded finite property-based adversarial tests.

Not source-distinct empirical data; a stress test for candidate implementation errors.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json,random,statistics,time
import compiler
from independent_oracle import oracle,verify_constructed_witness

SEED=20261021
TOTAL=500

def make(rng,i):
    n=rng.choice((3,4))
    protected=[rng.randrange(2) for _ in range(n)]
    if len(set(protected))==1 and i%3==0:protected[0]^=1
    readout=[rng.randrange(3) for _ in range(n)]
    ops=[]
    for k in range(rng.randrange(1,5)):
        if k%2==0:
            image=[rng.choice([j for j in range(n) if protected[j]==protected[x]]) for x in range(n)]
        else:
            image=[rng.randrange(n) for _ in range(n)]
        ops.append({'name':f'op{k}','image':image,'cost':rng.randrange(1,6)})
    allowed=['read']+[op['name'] for op in ops if rng.randrange(2)]
    return {'name':f'seeded-opaque-{i}','protected':protected,
       'readouts':[{'name':'read','values':readout,'cost':rng.randrange(1,4)}],
       'operations':ops,'grants':allowed,'base_readouts':['read'],
       'desired_labels':[rng.randrange(4) for _ in range(n)]}

def main():
    rng=random.Random(SEED)
    results={'seed':SEED,'models':TOTAL,'three_state':0,'four_state':0,'constructed':0,'obstructed':0,
             'cost_disagreements':0,'unresolved_disagreements':0,'unsafe_witnesses':0,'independently_validated_witnesses':0,
             'source_distinct_biology_or_author_contract':False}
    candidate_us=[];oracle_us=[]
    for i in range(TOTAL):
        src=make(rng,i)
        results['three_state' if len(src['protected'])==3 else 'four_state']+=1
        t=time.perf_counter_ns();v=compiler.compile_experiment(deepcopy(src));c=time.perf_counter_ns()
        o=oracle(deepcopy(src));e=time.perf_counter_ns()
        candidate_us.append((c-t)/1000);oracle_us.append((e-c)/1000)
        if v['status']!=o['status'] or v['basis_cost']!=o['basis_cost']:
            results['cost_disagreements']+=1;raise AssertionError((i,src,v,o))
        if sorted(v['unresolved_pairs'])!=sorted(o['unresolved_pairs']):
            results['unresolved_disagreements']+=1;raise AssertionError((i,src,v,o))
        if v['closure']['transformations']!=o['transformation_count']:
            raise AssertionError('Finite closure count mismatch')
        verify_constructed_witness(src,v)
        if v['status']=='EXACT_BASIS_CONSTRUCTED':
            results['constructed']+=1
            if v['basis']:results['independently_validated_witnesses']+=1
        else:results['obstructed']+=1
    # Fault injection: forged observable vectors must fail the verifier.
    from fixtures import bit_model
    true=bit_model();w=compiler.compile_experiment(true)
    forged=deepcopy(w);forged['basis'][0]['values'][0]^=1
    try:verify_constructed_witness(true,forged)
    except AssertionError:results['forged_witness_rejected']=True
    else:raise AssertionError('Independent checker accepted fabricated readout!')
    for corrupted in (
        {**true,'grants':['read_r','unauthorized']},
        {**true,'operations':true['operations']+[deepcopy(true['operations'][0])]},
        {**true,'operations':[{'name':'bad','image':[100]*4,'cost':2}]},
        {**true,'readouts':[{'name':'read_r','values':[0,1,0,1],'cost':0}]},
    ):
        try:compiler.compile_experiment(corrupted)
        except (AssertionError,ValueError,KeyError):pass
        else:raise AssertionError('Ill-typed or unauthorized model accepted')
    results['malformed_sources_rejected']=4
    results['time_descriptive_microseconds']={
        'candidate_median':round(statistics.median(candidate_us),2),
        'oracle_median':round(statistics.median(oracle_us),2),
        'candidate_total':round(sum(candidate_us),2),
        'oracle_total':round(sum(oracle_us),2),
        'limitations':'Python CPU timing only; neither includes real source/measurement acquisition; ordering candidate first'}
    p=Path(__file__).with_name('fuzz_result.json');p.write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_OPAQUE_FINITE_MUTATION_REPLAY_PASS',TOTAL,
          'NO_COST_OR_OBSTRUCTION_MISMATCH')
    print('FORGED_WITNESS_AND_UNAUTHORIZED_SOURCE_REJECTION_PASS')
    print('FUZZ_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())

if __name__=='__main__':main()