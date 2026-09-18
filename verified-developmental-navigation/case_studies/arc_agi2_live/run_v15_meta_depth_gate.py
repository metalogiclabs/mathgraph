import itertools, json
from pathlib import Path

HERE=Path(__file__).resolve().parent

# Real ARC evidence, copied only from completed immutable runs in this lineage.
ARC_LEVELS = {
  0: {
    'name':'task/program search',
    'evidence':['whole-grid depth-2 closure: 0/120 fits after 876264 candidates'],
    'complete_enough':True,
    'gain':False,
  },
  1: {
    'name':'representation/ontology search',
    'evidence':['local cell: 5 train / 0 heldout','single object: 0','pair roles/actions: 0','class quotient: 2 train / 0 heldout','spatial scene graph: 0 after 130368 candidates'],
    'complete_enough':True,
    'gain':True,
  },
  2: {
    'name':'policy-over-representations',
    'evidence':['symbolic relation change center(A)=border(B): 1 train / 0 heldout','only two tail policies tested after ontology change'],
    'complete_enough':False,
    'gain':True,
  },
  3: {
    'name':'policy-over-meta-policy',
    'evidence':[],
    'complete_enough':False,
    'gain':False,
  },
}

def adaptive_depth(levels):
    """Escalate only when the current level is adequately covered and still leaves a live obstruction.
    Stop at the first non-exhausted level: deeper recursion is not yet licensed by evidence.
    """
    d=0; trace=[]
    while True:
        x=levels[d]
        trace.append({'level':d,'name':x['name'],'complete_enough':x['complete_enough'],'gain':x['gain']})
        if not x['complete_enough']:
            return d,trace,'STOP_CURRENT_LEVEL_NOT_EXHAUSTED'
        if d+1 not in levels:
            return d,trace,'STOP_NO_HIGHER_LEVEL'
        d+=1


def exhaustive_toy_worlds(max_depth=4):
    """Finite sanity test: each world has a first depth at which a decisive move exists.
    Utility = 1 if the chosen depth can reach that move, minus a small cost per active level.
    This checks whether one globally fixed recursion depth can be optimal across all worlds.
    """
    rows=[]
    cost=0.1
    for required in range(max_depth+1):
        scores=[]
        for chosen in range(max_depth+1):
            success = chosen >= required
            utility=(1.0 if success else 0.0)-cost*chosen
            scores.append((utility,chosen,success))
        best=max(scores)[1]
        rows.append({'required_depth':required,'best_depth':best,'scores':[{'depth':d,'utility':u,'success':s} for u,d,s in scores]})
    bests=sorted({r['best_depth'] for r in rows})
    return rows,bests

def main():
    d,trace,stop=adaptive_depth(ARC_LEVELS)
    toy,bests=exhaustive_toy_worlds(4)
    result={
      'schema':'verified-developmental-navigation.meta-depth-gate.v15',
      'arc_replay':{
        'licensed_recursion_depth':d,
        'trace':trace,
        'stop_reason':stop,
        'interpretation':'Current ARC evidence licenses recursion through L2, but not escalation to L3: the symbolic relation family that L2 selected has not itself been covered. The next move is to PROBE/COMPLETE-COVER L2, not add another meta level.'
      },
      'finite_depth_test':{
        'worlds':toy,
        'distinct_optimal_depths':bests,
        'fixed_depth_universally_optimal':len(bests)==1,
        'interpretation':'With any positive per-level cost, the optimal recursion depth is state-dependent: activate only enough levels to reach the first decisive distinction. More recursion is harmful once it adds cost without new reach.'
      },
      'proposed_law':'Adaptive Recursion Law: apply the verified-development loop recursively only until the lowest non-exhausted level. Escalate from level k to k+1 only after a declared cover at k fails to yield a lawful decisive continuation; descend immediately when a higher-level change restores such a continuation.'
    }
    out=HERE/'results_v15_meta_depth_gate'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
