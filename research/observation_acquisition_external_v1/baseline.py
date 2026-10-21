"""Independent equal-information exhaustive search for finite observation programs."""
from itertools import product

def compare(worlds, transitions, readout, *, max_depth=4, max_nodes=100000):
    names=sorted(transitions)
    count=0
    for depth in range(max_depth+1):
        for sequence in product(names,repeat=depth):
            count+=1
            if count>max_nodes:return {"status":"UNKNOWN_BUDGET","visited":count}
            seen=set()
            for origin in worlds:
                x=origin
                for step in sequence:x=transitions[step][x]
                seen.add(readout[x])
            if len(seen)==len(worlds):
                return {"status":"FOUND","program":list(sequence),"visited":count}
    return {"status":"UNKNOWN_NO_WITNESS_IN_BOUNDED_GRAMMAR","visited":count}
