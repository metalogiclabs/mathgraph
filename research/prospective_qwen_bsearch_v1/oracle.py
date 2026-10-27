"""Precommitted source-only behavioral oracle for a Qwen C-to-Rust migration."""
from itertools import combinations_with_replacement
KEYS=(-3,-2,-1,0,1,2,3)
VALUES=(-2,-1,0,1,2)
MAX_LEN=5
EXPECTED_COUNT=1764

def cases():
    for length in range(MAX_LEN+1):
        for row in combinations_with_replacement(VALUES,length):
            for key in KEYS:
                yield row,key

def admissible(row,key,got):
    if type(got) is not int:
        return False
    matches={i for i,value in enumerate(row) if value==key}
    return got in matches if matches else got==len(row)

def contract_ground_truth(row,key):
    matches=[i for i,v in enumerate(row) if v==key]
    return {"valid_results":matches if matches else [len(row)],
            "input":list(row),"key":key}

def audit(original_output,target_output=None):
    all_cases=list(cases())
    if len(all_cases)!=EXPECTED_COUNT:
        raise AssertionError("FROZEN_CASE_CENSUS_CHANGED")
    source_bad=[]
    translated_bad=[]
    for row,key in all_cases:
        val=original_output(row,key)
        if not admissible(row,key,val):
            source_bad.append((row,key,val))
        if target_output is not None:
            got=target_output(row,key)
            if not admissible(row,key,got):
                translated_bad.append((row,key,got))
    return {"cases":len(all_cases),"source_violations":source_bad[:3],
            "target_violations":translated_bad[:3],
            "target_executed":target_output is not None,
            "verdict":("REJECTED_SOURCE_BASELINE" if source_bad else
                       "UNKNOWN_NOT_EXECUTABLE" if target_output is None else
                       "FINITE_COUNTEREXAMPLE" if translated_bad else
                       "WARRANTED_BOUNDED_MATCH")}
