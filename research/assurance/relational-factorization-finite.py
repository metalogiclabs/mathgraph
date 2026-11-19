"""Finite relational/factorization qualification; standard mathematics, not a new theorem.
Assumes finite S={0,1,2}, observation Y={0,1}, allowed outcomes V={0,1}.
Exhaustively compares per-fibre allowed-outcome intersections with explicit decoder search.
"""
from itertools import product
import json

S=(0,1,2)
Y=(0,1)
V=(0,1)
ALLOWED=(frozenset((0,)),frozenset((1,)),frozenset((0,1)))
stats={"total":0,"disagreements":0,"valid_decoder_exists":0,
       "no_valid_decoder":0,"equality_of_allowed_sets_too_strong":0}
for qtuple in product(Y,repeat=len(S)):
    q=dict(zip(S,qtuple))
    for permitted in product(ALLOWED,repeat=len(S)):
        allowed=dict(zip(S,permitted))
        fibres=[tuple(s for s in S if q[s]==y) for y in Y]
        feasible=all(bool(set.intersection(*(set(allowed[s]) for s in fibre)))
                     for fibre in fibres if fibre)
        brute=any(all(decoder[q[s]] in allowed[s] for s in S)
                  for decoder in (dict(zip(Y,d)) for d in product(V,repeat=len(Y))))
        assert feasible==brute
        stats["total"]+=1
        stats["disagreements"]+=int(feasible!=brute)
        stats["valid_decoder_exists"]+=int(brute)
        stats["no_valid_decoder"]+=int(not brute)
        too_strict=any(any(allowed[s]!=allowed[fibre[0]] for s in fibre)
                       for fibre in fibres if fibre)
        stats["equality_of_allowed_sets_too_strong"]+=int(brute and too_strict)
assert stats=={"total":216,"disagreements":0,"valid_decoder_exists":156,
               "no_valid_decoder":60,"equality_of_allowed_sets_too_strong":96}
print(json.dumps(stats,sort_keys=True))
