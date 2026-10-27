"""Preregistered source-only sentinel behavioral oracle."""
from itertools import combinations_with_replacement,product
VALUES=(-2,-1,0,1,2)
KEYS=(-3,-2,-1,0,1,2,3)
UINT_MAX=4294967295

def vectors(kind):
    if kind=="sorted_minus_one":
        for n in range(6):
            for row in combinations_with_replacement(VALUES,n):
                for key in KEYS:yield row,key
    elif kind=="unsorted_uintmax":
        for n in range(5):
            for row in product(VALUES,repeat=n):
                for key in KEYS:yield row,key
    else:raise ValueError("UNREGISTERED_CASE")

def authorized(kind,row,key,result):
    if type(result)!=int:return False
    matches={i for i,val in enumerate(row) if val==key}
    return result in matches if matches else result==(-1 if kind=="sorted_minus_one" else UINT_MAX)

def census():
    return {k:sum(1 for _ in vectors(k)) for k in ("sorted_minus_one","unsorted_uintmax")}

def evaluate(kind,observations):
    expected=census()[kind]
    if len(observations)!=expected:raise ValueError("INCOMPLETE_FROZEN_CORPUS")
    bad=[]
    for record in observations:
        row=tuple(record["row"])
        if not authorized(kind,row,record["key"],record["result"]) or not record["unchanged"]:
            bad.append(record)
    return {"total":expected,"violations":len(bad),"first_counterexample":bad[:1],
            "verdict":"FINITE_COUNTEREXAMPLE" if bad else "WARRANTED_BOUNDED_MATCH"}
