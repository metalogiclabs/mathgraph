#!/usr/bin/env python3
"""V8 — sparse verifier obstruction constrains a version space of regime repairs."""
from __future__ import annotations
from collections import Counter
from itertools import combinations
import json

N=6
VERTICES=tuple(range(N))
EDGES=tuple(combinations(VERTICES,2))
EDGE_INDEX={e:i for i,e in enumerate(EDGES)}


def canon_partition(p):
    return tuple(sorted((tuple(sorted(b)) for b in p)))

def set_partitions(items):
    items=tuple(items)
    if not items:
        return ((),)
    first=items[0]; out=set()
    for rest in set_partitions(items[1:]):
        out.add(canon_partition(((first,),)+rest))
        for i in range(len(rest)):
            blocks=[tuple(b) for b in rest]
            blocks[i]=tuple(sorted((first,)+blocks[i]))
            out.add(canon_partition(tuple(blocks)))
    return tuple(sorted(out))

PARTITIONS=set_partitions(VERTICES)
assert len(PARTITIONS)==203

# For each partition, precompute the edge mask that would be illegal because its
# endpoints lie in one quotient block. A conflict graph is admissible iff it has
# empty intersection with this mask.
PARTITION_DATA=[]
for p in PARTITIONS:
    internal=0
    for block in p:
        for u,v in combinations(block,2):
            internal |= 1 << EDGE_INDEX[(u,v)]
    PARTITION_DATA.append((len(p),internal,p))
PARTITION_DATA.sort(key=lambda x:(x[0],x[2]))

ALL_VERTEX_MASK=(1<<N)-1

def chromatic_number_dp(graph_mask:int)->int:
    """Independent subset-DP computation, not using the partition enumeration."""
    independent=[False]*(1<<N); independent[0]=True
    for s in range(1,1<<N):
        verts=[i for i in VERTICES if (s>>i)&1]
        independent[s]=all(not ((graph_mask>>EDGE_INDEX[(u,v)])&1) for u,v in combinations(verts,2))
    dp=[N+1]*(1<<N); dp[0]=0
    for s in range(1,1<<N):
        least=(s & -s).bit_length()-1
        sub=s
        while sub:
            if ((sub>>least)&1) and independent[sub]:
                dp[s]=min(dp[s],1+dp[s^sub])
            sub=(sub-1)&s
    return dp[ALL_VERTEX_MASK]

unique=0; ambiguous=0; max_optima=0
chromatic_distribution=Counter(); optimum_count_distribution=Counter(); joint=Counter()
examples={}

for graph_mask in range(1<<len(EDGES)):
    best=N+1; optima=[]
    for blocks,internal,p in PARTITION_DATA:
        if blocks>best:
            break
        if graph_mask & internal:
            continue
        if blocks<best:
            best=blocks; optima=[p]
        else:
            optima.append(p)
    assert optima

    # Independent decision route: minimum number of independent-set colors.
    chi=chromatic_number_dp(graph_mask)
    assert chi==best

    # Every retained partition is exactly an optimal proper coloring modulo
    # color-name permutation: its blocks are independent and count is chi.
    for p in optima:
        assert len(p)==chi
        for block in p:
            assert all(not ((graph_mask>>EDGE_INDEX[(u,v)])&1) for u,v in combinations(block,2))

    k=len(optima)
    chromatic_distribution[chi]+=1
    optimum_count_distribution[k]+=1
    joint[(chi,k)]+=1
    max_optima=max(max_optima,k)
    if k==1:
        unique+=1
    else:
        ambiguous+=1
        examples.setdefault(k,{"graph_mask":graph_mask,"chromatic_number":chi,"optima":[p for p in optima[:4]]})

assert unique+ambiguous==32768
assert unique==6203
assert ambiguous==26565
assert max_optima==27
assert chromatic_distribution=={1:1,2:5176,3:22377,4:5042,5:171,6:1}

result={
  "protocol":"DANIEL_OBSTRUCTION_VERSION_SPACE_V8",
  "verdict":"PASS_EXHAUSTIVE_SPARSE_OBSTRUCTION_VERSION_SPACE_AUDIT",
  "precommit":"99f7180c4c48e1dfa738bb65dd7965d5f4803626",
  "world":{"states":6,"possible_conflict_edges":15,"all_obstruction_graphs":32768,"all_partitions":203},
  "result":{"unique_coarsest_repair_graphs":unique,"ambiguous_coarsest_repair_graphs":ambiguous,"max_number_of_equally_coarse_repairs":max_optima,"chromatic_number_distribution":dict(sorted(chromatic_distribution.items())),"optimal_repair_count_distribution":dict(sorted(optimum_count_distribution.items()))},
  "independent_check":"minimum partition block count equals subset-DP chromatic number on all 32,768 graphs",
  "claim":"Sparse certified incompatibilities usually constrain a version space rather than determine one coarsest regime: 26,565/32,768 n=6 obstruction graphs have multiple optimal admissible partitions.",
  "boundary":"This is standard graph coloring/partition mathematics. It falsifies a universal unique-extension reading of obstruction; it does not choose among equally valid developmental continuations."
}
print(json.dumps(result,indent=2,sort_keys=True))
