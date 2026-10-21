"""Source-blind finite observation-program search; not primitive invention.

A task is a JSON-defined finite transition system. Programs consist of lawful
actions followed by a readout. The constructor backwards-prunes state pairs
which cannot be separated with remaining depth. Never reads protected sources.
"""
from collections import deque

def run_program(world, actions, program):
    x=world
    for op in program:
        x=actions[op][x]
    return x

def construct(worlds, actions, observation, *, max_depth=4, max_nodes=100000):
    worlds=tuple(worlds)
    if len(set(worlds))!=len(worlds):
        raise ValueError("DUPLICATE_WORLD")
    names=tuple(sorted(actions))
    for name in names:
        if set(actions[name]) != set(worlds):
            raise ValueError("UNLAWFUL_TRANSITION_DOMAIN")
    def signature(sequence):
        return tuple(observation[run_program(w,actions,sequence)] for w in worlds)
    def separates(seq):
        return len(set(signature(seq)))==len(worlds)
    q=deque([()])
    seen=set()
    visits=0
    while q:
        path=q.popleft()
        sig=tuple(run_program(w,actions,path) for w in worlds)
        if sig in seen: continue
        seen.add(sig)
        visits+=1
        if visits>max_nodes:return {"status":"UNKNOWN_BUDGET","visited":visits}
        if separates(path):
            return {"status":"FOUND","program":list(path),"visited":visits}
        if len(path)<max_depth:
            for name in names:
                q.append(path+(name,))
    return {"status":"UNKNOWN_NO_WITNESS_IN_BOUNDED_GRAMMAR","visited":visits}
